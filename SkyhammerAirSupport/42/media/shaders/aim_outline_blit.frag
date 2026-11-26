#version 120
uniform sampler2D texture;
uniform sampler2D mask;
varying vec4 vColor;
varying vec2 vUV;
void main() {
    vec4 body=texture2D(mask,vUV);
    vec4 edge=texture2D(texture,vUV);
    vec3 whiteMarker=vec3(32.0,64.0,128.0)/255.0;
    bool whiteHeat=distance(body.rgb,whiteMarker)<.012 || distance(edge.rgb,whiteMarker)<.012;
    if(whiteHeat) {
        // Preserve the moving mesh silhouette and antialiased boundary. A little
        // transparency retains clothing/body shading instead of a flat white icon.
        float a=max(body.a*.96,edge.a*(1.0-body.a)*.10);
        // IngameState draws model masks BEFORE RenderOffScreenBuffer. The screen
        // thermal shader applies black-hot inversion later; never invert twice.
        gl_FragColor=vec4(vec3(.985),a);
    } else {
        gl_FragColor=edge*vec4(1.0,1.0,1.0,1.0-body.a);
    }
}
