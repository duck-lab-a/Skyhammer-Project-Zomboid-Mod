import cv2, numpy as np, os, sys
OUT=r"C:/Users/user/Downloads/Skyhammer_스크린샷/2026-11-26"
def rd(p): return cv2.imdecode(np.fromfile(p,np.uint8),1)
def wr(p,im):
    q=94
    while True:
        ok,b=cv2.imencode('.jpg',im,[cv2.IMWRITE_JPEG_QUALITY,q])
        if len(b)<1_600_000 or q<80: break
        q-=2
    b.tofile(p); return len(b),q
def plate(im,clean,box,feather=3):
    x0,y0,x1,y1=box
    m=np.zeros(im.shape[:2],np.float32); m[y0:y1,x0:x1]=1
    m=cv2.GaussianBlur(m,(0,0),feather)[...,None]
    # only inside grown box
    return np.clip(im*(1-m)+clean*m,0,255).astype(np.uint8)
def inpaint(im,boxes,r=5):
    m=np.zeros(im.shape[:2],np.uint8)
    for x0,y0,x1,y1 in boxes: m[y0:y1,x0:x1]=255
    return cv2.inpaint(im,m,r,cv2.INPAINT_TELEA)
def mask_fill(im,circles=(),boxes=(),polys=(),r=4):
    m=np.zeros(im.shape[:2],np.uint8)
    for x,y,R in circles: cv2.circle(m,(x,y),R,255,-1)
    for a,b,c,d in boxes: m[b:d,a:c]=255
    for p in polys: cv2.fillPoly(m,[np.array(p,np.int32)],255)
    return cv2.inpaint(im,m,r,cv2.INPAINT_TELEA)
def deband(f):
    # smooth only flat areas (sky), keep edges; fine noise hides 8-bit steps
    b=cv2.GaussianBlur(f,(0,0),9); d=np.abs(f-b).max(2)/(b.mean(2)+.02)
    g=cv2.GaussianBlur((d<0.045).astype(np.float32),(0,0),3)[...,None]
    g=np.clip(g*1.3-.3,0,1)
    n=np.random.default_rng(1).normal(0,.004,f.shape[:2])[...,None].astype(np.float32)
    return f*(1-g)+(b+n)*g
def grade(im,lo=0.4,hi=99.7,bp=0.6,gamma=1.0,sat=1.15,clahe=1.2,sharp=0.55,shadow=0.0,wb=None,sky=False):
    f=im.astype(np.float32)/255
    if sky: f=deband(f)
    lum=f.mean(2)
    l=np.percentile(lum,lo)*bp; h=np.percentile(lum,hi); h=h+(1-h)*0.35
    f=np.clip((f-l)/(h-l),0,1)
    if gamma!=1: f=f**(1/gamma)
    if shadow: # lift dark parts only
        L=f.max(2,keepdims=True); w=np.clip((0.34-L)/0.34,0,1); w=cv2.GaussianBlur(w,(0,0),2)[...,None] if w.ndim==2 else cv2.GaussianBlur(w,(0,0),2)[...,None]; f=np.clip(f*(1+shadow*w*1.6),0,1)
    lab=cv2.cvtColor((f*255).astype(np.uint8),cv2.COLOR_BGR2LAB)
    if clahe:
        c=cv2.createCLAHE(clahe,(6,6)); lab[...,0]=cv2.addWeighted(lab[...,0],0.5,c.apply(lab[...,0]),0.5,0)
    ab=(lab[...,1:].astype(np.float32)-128)*sat+128
    lab[...,1:]=np.clip(ab,0,255)
    f=cv2.cvtColor(lab,cv2.COLOR_LAB2BGR)
    if sharp:
        b=cv2.GaussianBlur(f,(0,0),1.6); f=cv2.addWeighted(f,1+sharp,b,-sharp,0)
    return f
def crop(im,x,y,w):
    h=int(round(w*9/16)); assert x>=0 and y>=0 and x+w<=1920 and y+h<=1080,(x,y,w,h)
    c=im[y:y+h,x:x+w]
    return cv2.resize(c,(1920,1080),interpolation=cv2.INTER_LANCZOS4)
S={}
def shot(name,src,x,y,w,pre=None,**g):
    im=rd('g/'+src+'.png')
    if pre: im=pre(im)
    o=grade(crop(im,x,y,w),**g); S[name]=o
    print(name,wr(f"{OUT}/{name}.jpg",o))

import glob
for f in glob.glob(OUT+'/V[PA]_*.jpg'): os.remove(f)
def src(p): return rd(p)
def airmask(reg,thr=7,grow=1):
    """aircraft pixels = those that leave a smooth sky fitted to the box"""
    h,w=reg.shape[:2]; yy,xx=np.mgrid[0:h,0:w].astype(np.float32); xx=xx/w-.5; yy=yy/h-.5
    A=np.stack([np.ones_like(xx),xx,yy,xx*yy,xx*xx,yy*yy],-1).reshape(-1,6); f=cv2.GaussianBlur(reg,(0,0),.8).astype(np.float32).reshape(-1,3)
    ok=np.ones(len(A),bool); ed=np.zeros((h,w),bool); e=max(4,int(min(h,w)*.08)); ed[:e]=ed[-e:]=1; ed[:,:e]=ed[:,-e:]=1; ok=ed.reshape(-1).copy()
    for _ in range(4):
        C=np.linalg.lstsq(A[ok],f[ok],rcond=None)[0]; d=np.abs(f-A@C).max(1); ok=d<thr
    m=(d>thr).reshape(h,w).astype(np.uint8)
    m=cv2.morphologyEx(m,cv2.MORPH_CLOSE,np.ones((5,5),np.uint8))
    n,l,st,_=cv2.connectedComponentsWithStats(m); 
    if n>1:
        big=st[1:,4].max(); keep=np.isin(l,[i for i in range(1,n) if st[i,4]>big*.05]); m=keep.astype(np.uint8)
    # fill holes
    ff=cv2.copyMakeBorder(m,1,1,1,1,cv2.BORDER_CONSTANT,value=0); mk=np.zeros((h+4,w+4),np.uint8); cv2.floodFill(ff,mk,(0,0),2); full=(ff[1:-1,1:-1]!=2).astype(np.uint8); hole=((full==1)&(m==0)).astype(np.uint8)
    nh,lh,sh,_=cv2.connectedComponentsWithStats(hole)
    for i in range(1,nh):
        if sh[i,4]<30 and i: m[lh==i]=1          # (specks only: the sky seen through the airframe stays sky)
    m=m.astype(np.float32)
    return cv2.GaussianBlur(m,(0,0),.9)
def skyfill(im,box,pad=160,thr=8,avoid=()):
    """paint a UI box over clear sky with the sky fitted around it"""
    x0,y0,x1,y1=box; X0,Y0,X1,Y1=max(x0-pad,0),max(y0-pad,0),min(x1+pad,1920),min(y1+pad,1080)
    reg=cv2.GaussianBlur(im[Y0:Y1,X0:X1],(0,0),1.5).astype(np.float32); h,w=reg.shape[:2]
    yy,xx=np.mgrid[0:h,0:w].astype(np.float32); xx=xx/w-.5; yy=yy/h-.5
    A=np.stack([np.ones_like(xx),xx,yy,xx*yy,xx*xx,yy*yy],-1).reshape(-1,6); f=reg.reshape(-1,3)
    free=np.ones((h,w),bool); free[max(y0-Y0-6,0):y1-Y0+6,max(x0-X0-6,0):x1-X0+6]=0
    for a in avoid: free[max(a[1]-Y0,0):max(a[3]-Y0,0),max(a[0]-X0,0):max(a[2]-X0,0)]=0
    ok=free.reshape(-1).copy()
    for _ in range(5):
        C=np.linalg.lstsq(A[ok],f[ok],rcond=None)[0]; ok=free.reshape(-1)&(np.abs(f-A@C).max(1)<thr)
    fit=(A@C).reshape(h,w,3); fit+=np.random.default_rng(1).normal(0,.8,fit.shape)
    m=np.zeros((h,w),np.float32); m[y0-Y0:y1-Y0,x0-X0:x1-X0]=1
    mf=cv2.GaussianBlur(cv2.dilate(m,np.ones((9,9))),(0,0),5)*1.0; mf=np.maximum(mf,m)
    o=im.copy(); o[Y0:Y1,X0:X1]=np.clip(reg*0+im[Y0:Y1,X0:X1]*(1-mf[...,None])+fit*mf[...,None],0,255).astype(np.uint8); return o
DBG=[]
def S2(name,im,x,y,w,air=(),flame=0,dot=None,**g):
    dot=name.startswith('VP_') if dot is None else dot
    """air: ((x0,y0,x1,y1),(gain,contrast)) boxes in frame pixels holding an aircraft against clear sky"""
    im=im.copy()
    if dot: im=mask_fill(im,circles=[(960,540,5)],r=4)
    for (x0,y0,x1,y1),k in air:
        reg=im[y0:y1,x0:x1]; m=airmask(reg); DBG.append((name,(m*255).astype(np.uint8)))
        m0=m; m=cv2.GaussianBlur(cv2.erode((m>.5).astype(np.uint8),np.ones((3,3),np.uint8)).astype(np.float32),(0,0),.8); r=reg.astype(np.float32); mean=(r*m[...,None]).sum((0,1))/max(m.sum(),1)
        up=np.clip((r-mean)*k[1]+mean*k[0],0,255); bl=cv2.GaussianBlur(up,(0,0),1.4); up=np.clip(up*1.6-bl*.6,0,255)
        fl=cv2.GaussianBlur(cv2.dilate(((r[...,2]-r[...,0])>28).astype(np.uint8),np.ones((3,3),np.uint8)).astype(np.float32),(0,0),1.0)*flame; hot=np.clip(r*np.array([.95,1.12,1.3]),0,255); r=r*(1-fl[...,None])+hot*fl[...,None]; m=m*(1-fl)
        im[y0:y1,x0:x1]=np.clip(r*(1-m[...,None])+up*m[...,None],0,255).astype(np.uint8)
    o=grade(crop(im,x,y,w),**g); print(name,wr(f"{OUT}/{name}.jpg",o))
def apfill(im):
    o=im.copy(); src=cv2.GaussianBlur(im,(0,0),3).astype(np.float32)
    for y in range(588,812):
        c=src[y,1560:1596].mean(0); t=min(1,(y-588)/12)
        for x in range(1594,1660):
            u=min(1,(x-1594)/10)*t; o[y,x]=np.clip(im[y,x]*(1-u)+c*u,0,255)
    return o
V=dict(sky=True,clahe=0,sharp=.45)
S2('VP_1_apache',apfill(rd('g/n_ap2.png')),232,0,1420,air=[((760,4,1660,480),(1.3,1.75))],bp=.4,shadow=.45,sat=1.25,gamma=1.3,**V)
a=rd('g/n_a10b.png'); a=mask_fill(a,boxes=[(865,160,1065,216)],r=6)
S2('VP_2_a10',a,290,100,1240,air=[((1090,130,1560,400),(1.25,1.7))],bp=.4,shadow=.3,sat=1.2,gamma=1.28,**V)
S2('VP_2_a10_gunrun',rd('g/n_a10c.png'),0,92,1600,air=[((240,100,690,380),(1.05,1.6))],bp=.5,shadow=.4,sat=1.25,gamma=1.2,**V)
S2('VP_3_ac130',rd('g/n_ac1.png'),215,176,1030,air=(),bp=.4,shadow=.3,sat=1.2,gamma=1.28,**V)
S2('VP_4_b2',rd('g/n_b2p.png'),170,92,1370,air=[((640,120,1150,350),(1.35,1.45))],bp=.4,shadow=.4,sat=1.25,gamma=1.28,**V)
S2('VP_5_nuke',rd('g/vp_nuke1.png'),0,92,1600,bp=.95,sat=1.45,gamma=1.0,clahe=1.2,sky=False,sharp=.5)
# F-22: (a) one real frame, (b) the same pass, jets of successive frames laid over it
base=skyfill(rd('h/p348_04.png'),(640,0,1310,92),avoid=[(1050,94,1290,260)])
AIRF=[((1050,92,1290,260),(.95,1.7)),((650,425,760,485),(.85,1.4)),((676,540,726,560),(.85,1.4))]
S2('VP_6_f22_real',base,256,56,1110,flame=1,air=AIRF,bp=.4,shadow=.4,sat=1.25,gamma=1.3,**V)
comp=base.copy().astype(np.float32)
def lay(f,box):
    x0,y0,x1,y1=box; r=rd(f)[y0:y1,x0:x1]; m=airmask(r,9)[...,None]
    comp[y0:y1,x0:x1]=comp[y0:y1,x0:x1]*(1-m)+r*m
lay('h/p348_07.png',(915,250,1085,350))
lay('h/p348_11.png',(860,360,970,440))
cv2.imwrite('e/comp_dbg.png',comp.astype(np.uint8))
S2('VP_6_f22_formation',comp.astype(np.uint8),256,56,1110,flame=1,air=AIRF+[((915,250,1085,350),(.92,1.7)),((860,360,970,440),(.9,1.6))],bp=.4,shadow=.4,sat=1.25,gamma=1.3,**V)
S2('VP_6_f22_close',skyfill(rd('g/n_f22a.png'),(640,0,1310,94),avoid=[(1200,95,1520,330)]),440,62,1120,flame=1,air=[((1200,100,1520,330),(1.0,1.6))],bp=.4,shadow=.4,sat=1.25,gamma=1.28,**V)
# ---- vanilla
S2('VA_1_apache',mask_fill(rd('g/va_apache1.png'),polys=[[(957,534),(984,561),(973,562),(963,570),(957,568)]],r=3),0,110,1067,sat=1.05,shadow=.5,clahe=0,bp=.5,hi=99.9)
S2('VA_2_a10',mask_fill(rd('g/n_a10v.png'),circles=[(1293,318,17)]),0,92,1600,bp=.9,sat=1.35,clahe=1.0)
ac=mask_fill(rd('g/c_ac3.png'),boxes=[(1188,390,1222,430)],r=5)
S2('VA_3_ac130',ac,0,0,1600,sat=1.08,shadow=.15,clahe=.6,bp=.75)
cl=rd('g/p_174.0.png')
def clean(im,plate_box=True):
    im=plate(im,cl,(650,0,1300,92),2)
    return mask_fill(im,circles=[(1030,290,12)],boxes=[(952,277,966,303),(1097,277,1111,303),(1018,210,1044,224),(1018,356,1044,370)],r=5)
f19=rd('h/v168_19.png')
S2('VA_6_f22_real',clean(f19),150,120,1440,bp=.95,lo=1,sat=1.3,clahe=1.0,gamma=.95)
pl=rd('h/v168_12.png')
def shratio(f,box):
    x0,y0,x1,y1=box
    r=(rd(f)[y0:y1,x0:x1].astype(np.float32)+1)/(pl[y0:y1,x0:x1].astype(np.float32)+1)
    r=r.mean(2); r=cv2.GaussianBlur(r,(0,0),1.5); return np.where(r<.93,r,1.0)
R18=shratio('h/v168_18.png',(720,530,1280,930))
comp=clean(pl).astype(np.float32)
def stamp(R,x,y):
    h,w=R.shape; x1=min(x+w,1920); y1=min(y+h,1080); x0=max(x,0); y0=max(y,0)
    comp[y0:y1,x0:x1]*=cv2.GaussianBlur(R,(0,0),1.2)[y0-y:y1-y,x0-x:x1-x][...,None]
for x,y in ((70,112),(1085,226),(385,622)): stamp(R18,x,y)
S2('VA_6_f22_formation',comp.astype(np.uint8),60,100,1560,bp=.95,lo=1,sat=1.3,clahe=1.0,gamma=.95)
import b2fit      # (Skyhammer_Shadow.drawShadow's own square: half 27.77 tiles, 28.44 px a tile as fitted to B 410.8 / 411.0)
W=b2fit.lay(765,482,np.deg2rad(240),28.44)
lot=mask_fill(cl,boxes=[(1074,388,1112,434)],r=5).astype(np.float32)
S2('VA_4_b2',np.clip(lot*(1-.40*W[...,None]),0,255).astype(np.uint8),0,92,1600,bp=.95,lo=1,sat=1.3,clahe=.5,gamma=1.08)
