"""Reference-led architectural fabric, imperial ornament and spectacle props."""
import bpy,math,random,json
from math import pi,cos,sin
from pathlib import Path
from mathutils import Vector
R=Path(__file__).resolve().parents[1]

def build_dressing(B,spec):
    rng=random.Random(619);T=2*pi
    # Give the sand deck a real underside and thickness above the service rooms.
    for ob in list(bpy.data.objects):
        if not ob.name.startswith('SANDS/Deck_') or len(ob.data.polygons)!=1:continue
        me=ob.data;vs=[tuple(v.co) for v in me.vertices];n=len(vs)
        fs=[tuple(range(n)),tuple(range(2*n-1,n-1,-1))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
        new=bpy.data.meshes.new(me.name+'/Structural slab');new.from_pydata(vs+[(x,y,.0) for x,y,z in vs],[],fs);new.materials.append(B.M['sand']);new.materials.append(B.M['darkstone']);new.update()
        for poly in new.polygons:poly.material_index=0 if poly.index==0 else 1
        ob.data=new
    for x in range(-39,46,7):B.box('HYPOGEUM/Deck crossbeam',(x,0,-.29),(.36,61,.55),'wood',collection='HypogeumProps')
    for y in [-28,-14,0,14,28]:B.box('HYPOGEUM/Deck longitudinal beam',(4,y,-.47),(88,.3,.65),'wood',collection='HypogeumProps')
    def banner(name,center,rot,width,height,mat='red',emblem=True):
        nx,nz=8,18;v=[]
        for back in [0,.035]:
            for j in range(nz+1):
                t=j/nz
                for i in range(nx+1):
                    u=i/nx;x=(u-.5)*width;y=-.13-.13*sin(u*6*pi)*sin(t*pi/2)-.22*sin(t*pi)+back;z=center[2]-t*height+.24*sin(u*pi)*(t**14)
                    v.append((x,y,z))
        p=(nx+1)*(nz+1);f=[]
        for j in range(nz):
            for i in range(nx):
                k=j*(nx+1)+i;f.extend([(k,k+1,k+nx+2,k+nx+1),(p+k,p+k+nx+1,p+k+nx+2,p+k+1)])
        o=B.mesh(name,v,f,mat,'Banners','none');o.location=(center[0],center[1],0);o.rotation_euler.z=rot
        # Embroidered borders follow the same cloth fold profile.
        for side in [-1,1]:
            points=[]
            u=.05 if side<0 else .95
            for j in range(nz+1):
                t=j/nz;y=-.16-.13*sin(u*6*pi)*sin(t*pi/2)-.22*sin(t*pi);z=center[2]-t*height
                points.extend([((u-.5)*width-.045,y,z),((u-.5)*width+.045,y,z)])
            oo=B.mesh(name+'/Gold hem',points,[(2*j,2*j+1,2*j+3,2*j+2) for j in range(nz)],'gold','Banners','none');oo.location=(center[0],center[1],0);oo.rotation_euler.z=rot
        a=B.localpos(center,rot,(-width*.59,0,center[2]+.08));b=B.localpos(center,rot,(width*.59,0,center[2]+.08));B.beam(name+'/Hanging rod',a,b,.10,'gold','Banners')
        if emblem:
            # Laurel leaves are small shaped brass embroidery meshes rather than text decals.
            for side in [-1,1]:
                for k in range(8):
                    th=pi*.15+k*pi*.095;x=side*cos(th)*width*.24;z=center[2]-height*.66+sin(th)*width*.35
                    leaf=[(x,-.50,z-.16),(x+side*.17,-.54,z-.03),(x+side*.1,-.54,z+.20),(x-side*.06,-.51,z+.04)]
                    ob=B.mesh(name+'/Laurel',leaf,[(0,1,2,3)],'gold','Banners','none');ob.location=(center[0],center[1],0);ob.rotation_euler.z=rot
    # Crimson long facade standards punctuate rather than replace the carved bay rhythm.
    for i in range(0,64,4):
        a=T*(i+.5)/64;x,y=B.ellipse_pos(a,107.0,84.0)
        banner(f'FACADE/Standard{i}',(x,y,31.5),B.angle_frame(a),3.6,17.2)
    # Upper rim pennants and curved cloth shades frame the entire arena as in the reference.
    for i in range(64):
        a=T*(i+.5)/64;x,y=B.ellipse_pos(a,104.8,81.8)
        B.cylinder(f'VELARIUM/Mast{i}',(x,y,36.1),.085,5.8,'wood',8,collection='Canopies',collision='none')
        if i%2==0:banner(f'VELARIUM/Pennant{i}',(x,y,38.5),B.angle_frame(a),.95,3.2,'red' if i%4==0 else 'linen',False)
    for i in range(32):
        a0=T*i/32+.006;a1=T*(i+1)/32-.006
        vs=[]
        for j in range(9):
            t=j/8;r=94.6+t*9.7
            for k in range(9):
                s=k/8;a=a0+(a1-a0)*s;z=33.5+.9*t-1.0*sin(pi*t)-.55*sin(pi*s)
                vs.append((r*cos(a),(r-23)*sin(a),z))
        fs=[]
        for j in range(8):
            for k in range(8):
                q=j*9+k;fs.append((q,q+1,q+10,q+9));fs.append((q+9,q+10,q+1,q))
        B.mesh(f'VELARIUM/Canvas panel{i}',vs,fs,'faded' if i%3 else 'linen','Canopies','none')
        for a in [a0,a1]:
            p=(94.6*cos(a),71.6*sin(a),33.5);q=(104.3*cos(a),81.3*sin(a),34.4);B.beam('VELARIUM/Ridge rope',p,q,.055,'linen','Canopies')
    # The imperial marquee is the main red focal point on the rear interior axis.
    verts=[]
    for j in range(9):
        for i in range(13):
            x=-10.6+i*21.2/12;y=51.8+j*16.1/8;u=abs(x)/10.6;v=abs(y-59.85)/8.05;z=34.2-2.6*max(u,v)-.25*sin(pi*u)
            verts.append((x,y,z))
    faces=[]
    for j in range(8):
        for i in range(12):k=j*13+i;faces.extend([(k,k+1,k+14,k+13),(k+13,k+14,k+1,k)])
    B.mesh('VIP/Crimson canopy',verts,faces,'red','ImperialDecor','none')
    for x in [-7.4,7.4]:banner('VIP/Imperial hanging', (x,52.4,30.9),0,3.0,11.0,'red')
    banner('VIP/Rear tapestry',(0,66.25,29.8),0,5.8,10.1,'red')
    for x in [-10.6,10.6]:B.beam('VIP/Canopy side edge',(x,51.8,31.6),(x,67.9,31.6),.14,'gold','ImperialDecor')
    B.beam('VIP/Canopy front edge',(-10.6,51.8,31.6),(10.6,51.8,31.6),.16,'gold','ImperialDecor')
    # Sculpted throne, low benches and an imperial balcony rail.
    B.box('VIP/Throne seat',(0,62.5,19.4),(1.5,1.45,.4),'gold',collection='ImperialDecor')
    B.box('VIP/Throne back',(0,63.1,20.5),(1.6,.25,2.3),'gold',collection='ImperialDecor')
    B.box('VIP/Crimson cushion',(0,62.4,19.64),(1.2,1.1,.15),'red',collection='ImperialDecor',collision='none')
    for x in [-.75,.75]:B.box('VIP/Throne arm',(x,62.4,20.0),(.18,1.3,.18),'gold',collection='ImperialDecor')
    for x in [-5,5]:B.box('VIP/Noble bench',(x,60.5,19.0),(3.0,1.0,.55),'wood',collection='ImperialDecor')
    for x in range(-8,9):B.column('VIP/Balcony baluster',x,51.2,17.95,1.3,.10,'light','ImperialDecor')
    B.box('VIP/Balcony handrail',(0,51.2,19.35),(18,.4,.25),'light',collection='ImperialDecor')
    # Benches carry seated bodies without floating over the real terraced structure.
    for row in range(24):
        r=73.3+row*.86+(1.8 if row>=8 else 0)+(1.8 if row>=16 else 0);z=(5.15+row*.74)*1.3
        for sec in range(16):
            B.arc(f'CAVEA/Seat bench{row}_{sec}',r+.83,r-23+.83,r+.48,r-23+.48,z+.27,z+.43,T*sec/16+.022,T*(sec+1)/16-.022,'warm','Benches',n=9)
    # Four combat markers, two training racks, a holding cage and stowable hurdles.
    for i,(x,y) in enumerate([(-27,12),(21,17),(-23,-16),(29,-12)]):
        B.column(f'SANDS/Combat marker{i}',x,y,.4,2.4,.36,'stone','ArenaProps')
    for x,y in [(-39,3),(38,23)]:
        for dx in [-1.8,1.8]:B.box('SANDS/Weapon rack post',(x+dx,y,1.35),(.22,.3,1.9),'wood',collection='ArenaProps')
        B.beam('SANDS/Weapon rack beam',(x-2,y,2.15),(x+2,y,2.15),.16,'wood','ArenaProps')
        for k in range(6):B.beam('SANDS/Practice spear',(x-1.5+k*.6,y+.2,.4),(x-1.2+k*.6,y,2.7),.055,'woodlight','ArenaProps')
    for x,y in [(43,11)]:
        B.box('SANDS/Cage wooden floor',(x,y,.55),(6,4,.3),'wood',collection='ArenaProps')
        for xx in [-3,3]:
            for yy in [-2,2]:B.box('SANDS/Cage corner',(x+xx,y+yy,2.5),(.24,.24,4.0),'iron',collection='ArenaProps')
        for j in range(13):
            for yy in [-2,2]:B.box('SANDS/Cage bars',(x-3+j*.5,y+yy,2.5),(.065,.065,4),'iron',collection='ArenaProps')
        for j in range(9):
            for xx in [-3,3]:B.box('SANDS/Cage end bars',(x+xx,y-2+j*.5,2.5),(.065,.065,4),'iron',collection='ArenaProps')
        for j in range(9):B.box('SANDS/Cage roof',(x,y-2+j*.5,4.53),(6.2,.07,.07),'iron',collection='ArenaProps')
    # Controlled soft-edged wear/stains: irregular thin polygons in combat zones.
    for k in range(42):
        x=rng.uniform(-48,48);y=rng.uniform(-30,30)
        if 44<x and abs(y)<6:continue
        rr=rng.uniform(.22,1.2);v=[(x,y,.407)]
        for j in range(12):
            a=T*j/12;r=rr*rng.uniform(.6,1.4);v.append((x+cos(a)*r*1.9,y+sin(a)*r,.407))
        B.mesh('SANDS/Old spectacle stain',v,[(0,j+1,(j+1)%12+1) for j in range(12)],'blood' if k%4==0 else 'warm','ArenaProps','none')
    # Four ceremonial braziers, continued smaller torches around the concourse.
    for i,(x,y) in enumerate([(-20,-87),(20,-87),(-109,12),(109,12)]):
        B.column('PLAZA/Brazier pedestal',x,y,0,2.4,.68,'light','Braziers')
        B.cylinder('PLAZA/Brazier bowl',(x,y,2.8),1.2,.7,'iron',24,r2=1.5,collection='Braziers')
        B.cylinder('PLAZA/Hot coals',(x,y,3.14),1.32,.05,'flame',24,collection='Braziers',collision='none')
        for j in range(7):
            a=T*j/7;B.cylinder('PLAZA/Flame',(x+.65*cos(a),y+.65*sin(a),3.48),.20,.7,'flame',5,r2=.005,collection='Braziers',collision='none')
        ld=bpy.data.lights.new('Plaza brazier'+str(i),'POINT');ld.energy=420;ld.color=(1,.36,.09);ld.shadow_soft_size=1;lo=bpy.data.objects.new(ld.name,ld);B.coll('Lighting').objects.link(lo);lo.location=(x,y,3.7);lo['distance']=24
    for i in range(0,64,4):
        a=T*i/64;x,y=B.ellipse_pos(a,101,78)
        B.box('CONCOURSE/Torch bracket',(x,y,4.2),(.22,.25,1.6),'iron',collection='Braziers',collision='none')
        B.cylinder('CONCOURSE/Coal sconce',(x,y,5.1),.25,.35,'flame',8,r2=.05,collection='Braziers',collision='none')
    # Fix paving surface ownership at the inter-district joins.
    for o in bpy.data.objects:
        if o.name.startswith('DISTRICT/Side street') or o.name.startswith('DISTRICT/North temple street'):o.location.z+=.02
    # An open stair throat through the two podium bays; architecture elsewhere is preserved.
    for o in list(bpy.data.objects):
        if (any(o.name.startswith(f'PODIUM/Gate{s}/') for s in [2,10]) and ('voussoir' in o.name or 'spandrel' in o.name)) or o.name=='PODIUM/Inner coping':bpy.data.objects.remove(o,do_unlink=True)
    for s in range(16):
        a0=T*s/16;gap=.042 if s in [2,10] else .0
        nextgap=.042 if (s+1)%16 in [2,10] else 0
        B.arc('PODIUM/Accessible coping',73.3,50.3,70.2,47.2,5.05*1.3,5.3*1.3,a0+gap,a0+T/16-nextgap,'light','Podium',n=16)
    return {'exteriorStandards':16,'upperShadePanels':32,'rimMasts':64,'tierBenches':384,'imperialCanopy':True,'braziers':4}
