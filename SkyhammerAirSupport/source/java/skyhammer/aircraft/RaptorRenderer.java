package skyhammer.aircraft;

import java.nio.FloatBuffer;
import org.joml.Matrix4f;
import org.lwjgl.BufferUtils;
import org.lwjgl.opengl.*;
import viewpoint.render.FrameContext;
import viewpoint.render.SceneData;

/** The F-22 flight: one mesh drawn once per jet; separate failure state and GL resources from the other aircraft. */
final class RaptorRenderer {
    private static int program,vao,vbo,count,uMvp,uPlain,uPrevious,uModel,uLight,uEye,uSpin,uPrevSpin,uFlash;
    private static boolean failed,history,announced;
    private static long lastFrame,lastRun=Long.MIN_VALUE;
    private static double lastElapsed;
    private static final Matrix4f model=new Matrix4f(),mvp=new Matrix4f(),plain=new Matrix4f();
    private static final Matrix4f[] previous=new Matrix4f[Raptor.JETS.length];
    static { for(int i=0;i<previous.length;i++)previous[i]=new Matrix4f(); }
    private static final FloatBuffer matrix=BufferUtils.createFloatBuffer(16);
    private static final int[] oldBuffers=new int[4];
    private static final int[] buffers={GL30.GL_COLOR_ATTACHMENT0,GL30.GL_COLOR_ATTACHMENT1,GL30.GL_COLOR_ATTACHMENT2,GL30.GL_COLOR_ATTACHMENT3};
    private RaptorRenderer() {}
    static void drawSafely(FrameContext frame) {
        if(failed||!Main.supported)return;
        AircraftBridge.RaptorSample s=AircraftBridge.raptor;
        long now=System.nanoTime();
        if(s==null){history=false;return;}
        // Lua sends the saved combat clock once a tick; between ticks the jets go on at most 1/20 s
        // (6 tiles), so a frame drawn between two ticks does not stutter and a pause holds them.
        double e=s.elapsed()+Math.min(.05,Math.max(0,(now-s.at())*1e-9));
        if(e<Raptor.FROM||e>=Raptor.END){history=false;return;}
        try {
            draw(frame,s,e,now);
            if(!announced){announced=true;System.out.println("[SkyhammerAircraft] F-22 flight drawn; "+count/3+" triangles a jet");}
        } catch(Throwable t) {
            failed=true;
            System.err.println("[SkyhammerAircraft] F-22 visual disabled: "+t);
            t.printStackTrace();
        }
    }
    private static void draw(FrameContext f,AircraftBridge.RaptorSample s,double e,long now)throws Exception {
        int oldProgram=GL11.glGetInteger(GL20.GL_CURRENT_PROGRAM);
        int oldVao=GL11.glGetInteger(GL30.GL_VERTEX_ARRAY_BINDING);
        int oldVbo=GL11.glGetInteger(GL15.GL_ARRAY_BUFFER_BINDING);
        for(int i=0;i<4;i++)oldBuffers[i]=GL11.glGetInteger(GL20.GL_DRAW_BUFFER0+i);
        GL11.glPushAttrib(GL11.GL_ALL_ATTRIB_BITS);
        try {
            if(program==0)init();
            SceneData scene=f.scene;
            boolean fresh=!history||s.run()!=lastRun||now-lastFrame>250_000_000L||e<lastElapsed;
            GL20.glUseProgram(program);
            // uFlash 1: part 5, the afterburner flames, always lit
            GL20.glUniform1f(uSpin,0);GL20.glUniform1f(uPrevSpin,0);GL20.glUniform1f(uFlash,1);
            GL20.glUniform3f(uLight,scene.daylightKnown?scene.daylightR:.6f,scene.daylightKnown?scene.daylightG:.6f,scene.daylightKnown?scene.daylightB:.6f);
            GL20.glUniform3f(uEye,f.eyeX,f.eyeY,f.eyeZ);
            GL20.glDrawBuffers(buffers);
            GL11.glEnable(GL11.GL_DEPTH_TEST);GL11.glDepthFunc(GL11.GL_LEQUAL);GL11.glDepthMask(true);
            GL11.glDisable(GL11.GL_BLEND);GL11.glDisable(GL11.GL_CULL_FACE);
            GL11.glEnable(GL11.GL_STENCIL_TEST);GL11.glStencilMask(255);
            GL11.glStencilFunc(GL11.GL_ALWAYS,1,255);GL11.glStencilOp(GL11.GL_KEEP,GL11.GL_KEEP,GL11.GL_REPLACE);
            GL11.glDisable(GL11.GL_SCISSOR_TEST);GL11.glColorMask(true,true,true,true);
            GL30.glBindVertexArray(vao);
            for(int i=0;i<Raptor.JETS.length;i++){
                Raptor.Pose p=Raptor.pose(i,e,s.x(),s.y(),s.floor(),s.heading(),s.altitude());
                if(!p.visible())continue;
                model.translation((float)(-p.x()-scene.originX),(float)(p.height()-scene.originY),(float)(-p.y()-scene.originZ))
                    .rotateY((float)p.yaw()).scale((float)s.scale());
                f.viewProjection.mul(model,mvp);scene.projection.mul(f.view,plain).mul(model);
                if(fresh)previous[i].set(plain);
                upload(uMvp,mvp);upload(uPlain,plain);upload(uPrevious,previous[i]);upload(uModel,model);
                GL11.glDrawArrays(GL11.GL_TRIANGLES,0,count);
                previous[i].set(plain);
            }
            lastFrame=now;lastRun=s.run();lastElapsed=e;history=true;
        } finally {
            GL30.glBindVertexArray(oldVao);GL15.glBindBuffer(GL15.GL_ARRAY_BUFFER,oldVbo);
            GL20.glUseProgram(oldProgram);GL11.glPopAttrib();GL20.glDrawBuffers(oldBuffers);
        }
    }
    private static void upload(int location,Matrix4f value){matrix.clear();value.get(matrix);GL20.glUniformMatrix4fv(location,false,matrix);}
    private static int uniform(String name){return GL20.glGetUniformLocation(program,name);}
    // The two engine nozzles' exits in f22.mesh (metres, +X starboard, +Y up, +Z nose), read off the
    // mesh's rear view: rectangular openings about 0.9 x 0.25 m.
    private static final float[] NOZZLE_X={-.71f,.71f};
    private static final float NOZZLE_Y=-1.11f,NOZZLE_Z=-7.62f;
    private static final int FLAME_SIDES=10;
    /** An afterburner flame: a flat cone from a nozzle 3.2 m back, yellow-white at the nozzle, orange at the tip. */
    private static void flame(FloatBuffer out,float x,float y,float z){
        float[] tip={x,y,z-3.2f};
        for(int i=0;i<FLAME_SIDES;i++){
            double a=2*Math.PI*i/FLAME_SIDES,b=2*Math.PI*(i+1)/FLAME_SIDES;
            float[] p={x+.40f*(float)Math.cos(a),y+.11f*(float)Math.sin(a),z};
            float[] q={x+.40f*(float)Math.cos(b),y+.11f*(float)Math.sin(b),z};
            org.joml.Vector3f n=new org.joml.Vector3f(q).sub(new org.joml.Vector3f(p))
                .cross(new org.joml.Vector3f(tip).sub(new org.joml.Vector3f(p))).normalize();
            for(float[] v:new float[][]{p,q,tip}){
                boolean end=v==tip;
                out.put(v).put(n.x).put(n.y).put(n.z).put(1f).put(end?.42f:.82f).put(end?.10f:.50f).put(5f);
            }
        }
    }
    private static void init()throws Exception {
        try {
            // uSpin stays 0, so f22.mesh's few part-1 faces (a nose panel) never turn; the two afterburner
            // flames added here are part 5, which aircraft.frag draws as its glowing flash.
            program=AircraftRenderer.program("aircraft.vert","aircraft.frag");
            uMvp=uniform("uMvp");uPlain=uniform("uPlain");uPrevious=uniform("uPrevious");uModel=uniform("uModel");
            uSpin=uniform("uSpin");uPrevSpin=uniform("uPrevSpin");uFlash=uniform("uFlash");
            uLight=uniform("uLight");uEye=uniform("uEye");
            FloatBuffer mesh=AircraftRenderer.mesh("f22.mesh");
            FloatBuffer vertices=BufferUtils.createFloatBuffer(mesh.remaining()+2*FLAME_SIDES*3*10);
            vertices.put(mesh);
            for(float x:NOZZLE_X)flame(vertices,x,NOZZLE_Y,NOZZLE_Z);
            vertices.flip();count=vertices.remaining()/10;
            vao=GL30.glGenVertexArrays();GL30.glBindVertexArray(vao);
            vbo=GL15.glGenBuffers();GL15.glBindBuffer(GL15.GL_ARRAY_BUFFER,vbo);GL15.glBufferData(GL15.GL_ARRAY_BUFFER,vertices,GL15.GL_STATIC_DRAW);
            for(int i=0;i<4;i++){GL20.glEnableVertexAttribArray(i);GL20.glVertexAttribPointer(i,i==3?1:3,GL11.GL_FLOAT,false,40,i*12L);}
        }catch(Exception e){
            if(vbo!=0)GL15.glDeleteBuffers(vbo);if(vao!=0)GL30.glDeleteVertexArrays(vao);
            if(program!=0)GL20.glDeleteProgram(program);program=vao=vbo=0;throw e;
        }
    }
}
