import cv2, numpy as np
TEX=cv2.imdecode(np.fromfile(r'C:\Users\user\Zomboid\mods\SkyhammerAirSupport\42\media\ui\SH_Shadow_B2.png',np.uint8),cv2.IMREAD_UNCHANGED)[...,3].astype(np.float32)/255
E=27.77
def quad(cx,cy,h,k,s=1.0):
    fx,fy=np.cos(h),np.sin(h); rx,ry=-fy,fx; o=[]
    for f,r in ((1,-1),(1,1),(-1,1),(-1,-1)):
        wx=(fx*f+rx*r)*E*s; wy=(fy*f+ry*r)*E*s
        o.append((cx+(wx-wy)*k, cy+(wx+wy)*k/2))
    return np.float32(o)
def lay(cx,cy,h,k,size=(1920,1080),sc=1.0):
    n=TEX.shape[0]
    M=cv2.getPerspectiveTransform(np.float32([(0,0),(n,0),(n,n),(0,n)]),quad(cx,cy,h,k)*sc)
    return cv2.warpPerspective(TEX,M,(int(size[0]*sc),int(size[1]*sc)),flags=cv2.INTER_LINEAR)
if __name__=='__main__':
    pl=cv2.imread('h/b2plate.png').astype(np.float32); sc=.25
    T=[]
    for i in (8,16):
        f=cv2.imread(f'b2scan/f_{i+1:03d}.png').astype(np.float32); r=(f+4)/(pl+4); sp=r.max(2)-r.min(2); m=cv2.GaussianBlur(r.mean(2),(0,0),3)
        val=((sp<.2)&(m<1.08)).astype(np.float32); val[:92,640:1310]=0; val[:120,1740:]=0; val[110:240,1860:]=0; val[590:,1600:]=0; val[990:]=0
        T.append((cv2.resize(1-np.clip(m,0,1),None,fx=sc,fy=sc,interpolation=cv2.INTER_AREA),cv2.resize(val,None,fx=sc,fy=sc,interpolation=cv2.INTER_AREA)))
    rng=np.random.default_rng(0)
    def cost(p,k,a):
        c=0
        for (d,v),(cx,cy) in zip(T,((p[1],p[2]),(p[3],p[4]))):
            w=lay(cx,cy,p[0],k,sc=sc)*a; c+=(v*(w-d)**2).sum()/v.sum()
        return c
    for k in (25.6,28.44,32):
        best=None
        for h0 in np.deg2rad(np.arange(0,360,15)):
            p=np.array([h0,900,-150,700,0.]); c=cost(p,k,.47)
            st=np.array([.25,300,200,300,200])
            for it in range(260):
                q=p+rng.normal(0,1,5)*st*(0.985**it); cq=cost(q,k,.47)
                if cq<c: p,c=q,cq
            if best is None or c<best[0]: best=(c,p)
        c,p=best
        for it in range(900):
            q=p+rng.normal(0,1,5)*np.array([.05,40,40,40,40])*(0.995**it); cq=cost(q,k,.47)
            if cq<c: p,c=q,cq
        print(k,round(c,5),'heading',round(np.rad2deg(p[0])%360,1),p[1:].round())
