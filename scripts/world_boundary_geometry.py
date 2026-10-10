"""Irregular fortified city edge, river continuations and rolling outer landscape."""
from pathlib import Path
from collections import Counter
import bpy,math,json,random,hashlib
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from city import CityGeometry,_collection,_material,_cypress_proto,_pine_proto,_house_proto
R=Path(__file__).resolve().parents[1]
T=math.tau

def point_segment(p,a,b):
    dx,dy=b[0]-a[0],b[1]-a[1];t=max(0,min(1,((p[0]-a[0])*dx+(p[1]-a[1])*dy)/(dx*dx+dy*dy)))
    q=(a[0]+dx*t,a[1]+dy*t)
    return math.dist(p,q),q,t

def smooth(t):t=max(0,min(1,t));return t*t*(3-2*t)

def apply(B):
    raw=(R/'master_world_boundary.json').read_bytes();plan=json.loads(raw)
    assert not bpy.data.collections.get('World_Boundary'),'Boundary already integrated'
    collection=_collection('World_Boundary');land=_collection('Outer_Landscape');rng=random.Random(827361)
    before=set(bpy.data.objects);retired=[]
    for obj in list(bpy.data.objects):
        if obj.name.startswith('Roman_hills/') or obj.get('semantic')=='landscape/hills':
            retired.append(obj.name);bpy.data.objects.remove(obj,do_unlink=True)
    wall=plan['wall'];poly=wall['centerline'];base=-.035;height=wall['height'];thickness=wall['thickness']
    gate_windows={}
    gate_frames={}
    # Openings are cut from complete masonry spans; the real portal fills each gap.
    for gate in plan['gates']:
        p=gate['center'][:2]
        _,idx,t=min((point_segment(p,a,b)[0],i,point_segment(p,a,b)[2]) for i,(a,b) in enumerate(zip(poly,poly[1:]+poly[:1])))
        a,b=poly[idx],poly[(idx+1)%len(poly)];length=math.dist(a,b);angle=math.atan2(b[1]-a[1],b[0]-a[0])
        gate_frames[gate['id']]={'center':[a[0]+t*(b[0]-a[0]),a[1]+t*(b[1]-a[1])],'rotation':angle}
        # A vertex gate intersects two wall segments. Cut both incident spans.
        radius=(gate['width']+2.4)/2+.2
        for j,(u,v) in enumerate(zip(poly,poly[1:]+poly[:1])):
            distance,q,f=point_segment(p,u,v)
            if distance>=radius:continue
            extent=math.sqrt(radius*radius-distance*distance);size=math.dist(u,v)
            gate_windows.setdefault(j,[]).append((max(0,f*size-extent),min(size,f*size+extent)))
    river_spans=[]
    for i,(a,b) in enumerate(zip(poly,poly[1:]+poly[:1])):
        if (a[0]<-190 and b[0]>-170) or (b[0]<-190 and a[0]>-170):
            if abs(a[1]-b[1])<15:river_spans.append(i)
    def span(name,a,b):
        length=math.dist(a,b)
        if length<.05:return
        angle=math.atan2(b[1]-a[1],b[0]-a[0]);mid=((a[0]+b[0])/2,(a[1]+b[1])/2)
        g=CityGeometry()
        g.box('stone',(0,0,base+height/2),(length+.08,thickness,height))
        g.box('light',(0,0,base+.30),(length+.16,thickness+.35,.60))
        for z in [height*.44,height-.45]:g.box('warm',(0,0,base+z),(length+.12,thickness+.18,.19))
        g.box('light',(0,0,base+height-.03),(length+.2,thickness+.30,.28))
        for side in [-1,1]:
            g.box('stone',(0,side*(thickness/2-.17),base+height+.30),(length+.1,.4,.65))
            count=max(1,int(length/2.6))
            for k in range(count):g.box('light',(-length/2+(k+.5)*length/count,side*(thickness/2-.15),base+height+.96),(1.28,.58,1.35))
        # Recessed joint geometry gives nearby wall courses a consistent scale.
        for z in [.9,1.7,2.5,3.3,4.1,4.9,5.7,6.5,7.3]:
            for side in [-1,1]:g.box('mortar',(0,side*(thickness/2+.006),z),(length,.022,.027))
        objects=g.objects(name,collection,B.M,'solid','world_boundary/wall')
        for obj in objects:obj.location=(*mid,0);obj.rotation_euler.z=angle
    for i,(a,b) in enumerate(zip(poly,poly[1:]+poly[:1])):
        if i in river_spans:continue
        length=math.dist(a,b);cuts=sorted(gate_windows.get(i,[]));cursor=0
        for start,end in cuts+[(length,length)]:
            p=[a[k]+(b[k]-a[k])*cursor/length for k in range(2)];q=[a[k]+(b[k]-a[k])*start/length for k in range(2)]
            span(f'CITYWALL/Span{i:02}_{cursor:.1f}',p,q);cursor=max(cursor,end)
    def tower(name,x,y,angle,h=12.4,w=6.8):
        # Complete floors and load-bearing perimeter walls with deep upper windows.
        for z in [.12,4.3,8.5,h-.3]:B.box(name+'/Floor',(x,y,z),(w,w,.28),'stone',angle,collection='World_Boundary')
        for side in range(4):
            a=angle+side*math.pi/2;cx=x+math.sin(a)*(w/2-.55);cy=y-math.cos(a)*(w/2-.55)
            B.box(name+'/Lower wall',(cx,cy,2.5),(w,1.1,5),'stone',a,collection='World_Boundary')
            B.arch(name+'/Window'+str(side),(cx,cy,5),a,1.35,1.25,3.5,1.1,w,'stone','World_Boundary',segments=10)
            B.box(name+'/Upper wall',(cx,cy,(8.5+h)/2),(w,1.1,h-8.5),'stone',a,collection='World_Boundary')
            B.box(name+'/Parapet',(cx,cy,h+.22),(w,1.2,.55),'light',a,collection='World_Boundary')
            for u in [-2.55,-.85,.85,2.55]:
                px=cx+u*math.cos(a);py=cy+u*math.sin(a)
                B.box(name+'/Merlon',(px,py,h+.84),(1.02,1.35,1.22),'light',a,collection='World_Boundary')
    tower_count=0
    for i,p in enumerate(poly):
        if i%2 or any(math.dist(p,g['center'][:2])<18 for g in plan['gates']+plan['watergates']):continue
        if -205<p[0]<-153:continue
        a=poly[(i+1)%len(poly)];tower(f'CITYWALL/Tower{i:02}',*p,math.atan2(a[1]-p[1],a[0]-p[0]),11.8+(i%3)*.7);tower_count+=1
    for gate in plan['gates']:
        frame=gate_frames[gate['id']];x,y=frame['center'];a=frame['rotation'];w=gate['width'];spring=4.5;top=spring+w/2+1.3
        name='CITYGATE/'+gate['id'];B.arch(name,(x,y,base),a,w,spring,top,4.2,w+2.4,'stone','World_Boundary',segments=22)
        for side in [-1,1]:
            dx=side*(w/2+4.4);tower(name+'/Flanking tower'+str(side),x+dx*math.cos(a),y+dx*math.sin(a),a,top+2.4,6.8)
            # Wood leaves exactly follow the arched opening, with real panel thickness.
            x0,x1=(-w/2+.08,-.04) if side<0 else (.04,w/2-.08)
            cross=[(x0,base+.03),(x1,base+.03)]
            cross +=[(u,base+spring+math.sqrt(max(0,(w/2-.08)**2-u*u))-.03) for u in [x1+(x0-x1)*i/20 for i in range(21)]]
            vs=[(u,v,z) for v in [-.25,.25] for u,z in cross];n=len(cross)
            fs=[tuple(range(n-1,-1,-1)),tuple(range(n,2*n))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
            obj=B.mesh(name+'/Closed oak leaf'+str(side),vs,fs,'wood','World_Boundary');obj.location=(x,y,0);obj.rotation_euler.z=a
            for z in [1.2,3.1,4.7]:
                for v in [-.29,.29]:
                    cx=x+(x0+x1)/2*math.cos(a)-v*math.sin(a);cy=y+(x0+x1)/2*math.sin(a)+v*math.cos(a)
                    B.box(name+'/Iron strap',(cx,cy,z),(x1-x0,.075,.15),'iron',a,collection='World_Boundary')
    for gate in plan['watergates']:
        x,y=gate['center'][:2]
        for side in [-1,1]:B.arch('WATERGATE/'+gate['id']+str(side),(x+side*10.7,y,-5.5),0,18.2,7.4,19.3,4.2,21.4,'stone','World_Boundary',segments=24)
        B.box('WATERGATE/'+gate['id']+'/Walkway',(x,y,13.7),(45,5,.45),'light',collection='World_Boundary')
        for u in range(-21,22,3):
            for yy in [-2.1,2.1]:B.box('WATERGATE/Merlon',(x+u,y+yy,14.45),(1.3,.6,1.4),'light',collection='World_Boundary')
    # The terrain extends far beyond the physical city limits and hides rectangular pavement edges.
    river_lines=[]
    for watergate in plan['watergates']:
        pts=[p[:2] for p in watergate['riverContinuation']];a,b=pts[-2:];dx,dy=b[0]-a[0],b[1]-a[1]
        pts.append([b[0]+dx*16,b[1]+dy*16]);river_lines.append(pts)
    def river_distance(x,y):return min(point_segment((x,y),a,b)[0] for line in river_lines for a,b in zip(line,line[1:]))
    def hills(x,y):
        peaks=[(-70,640,104,230,170),(242,590,81,170,190),(525,180,76,180,240),(-490,190,51,160,240),(55,-430,31,280,170),(-395,-330,33,190,180)]
        h=sum(z*math.exp(-((x-a)/sx)**2-((y-b)/sy)**2) for a,b,z,sx,sy in peaks)
        return h+8*(.5+.5*math.sin(x*.013+y*.009))*math.sin(y*.017-x*.006)**2
    ring=[]
    for a,b in zip(poly,poly[1:]+poly[:1]):
        count=max(2,math.ceil(math.dist(a,b)/7))
        for i in range(count):ring.append([a[k]+(b[k]-a[k])*i/count for k in range(2)])
    normals=[]
    for p in ring:
        dx,dy=p[0],p[1]-90;length=math.hypot(dx,dy);normals.append((dx/length,dy/length))
    distances=list(range(0,81,4))+list(range(88,241,8))+list(range(256,513,16))+[550,600,670,750,850,1000,1200,1450]
    vs=[];fs=[];face_materials=[]
    for d in distances:
        for p,n in zip(ring,normals):
            x,y=p[0]+n[0]*d,p[1]+n[1]*d
            z=-.045+smooth(d/45)*hills(x,y)+smooth(d/4)*.16
            rd=river_distance(x,y)
            if rd<24:z=-5.1
            elif rd<155:
                # A broad valley, with a narrow low bank, avoids a cut trench.
                bank=-5.1+5.25*smooth((rd-24)/15)
                z=bank+max(0,z-.15)*smooth((rd-36)/119)
            vs.append((x,y,z))
    count=len(ring)
    for j in range(len(distances)-1):
        for i in range(count):
            q=j*count+i;n=j*count+(i+1)%count
            fs.append((q+count,n+count,n,q))
            x,y,z=vs[q];v=math.sin(x*.016+y*.012)+math.sin(y*.031-x*.009)
            face_materials.append(2 if z>80 else 1 if v>.9 else 3 if v<-.75 else 0)
    terrain_mats=[B.material('Continuous Mediterranean earth',(.34,.325,.23),.98,texture='mediterranean_earth.png')]
    terrain=B.mesh('LANDSCAPE/Continuous outer hills',vs,fs,terrain_mats[0],'Outer_Landscape','solid')
    for mat in terrain_mats[1:]:terrain.data.materials.append(mat)
    for p in terrain.data.polygons:p.material_index=0;p.use_smooth=True
    for li,loop in enumerate(terrain.data.loops):
        v=terrain.data.vertices[loop.vertex_index].co
        terrain.data.uv_layers.active.data[li].uv=(v.x/96,v.y/96)
    assert all(p.normal.z>0 for p in terrain.data.polygons),'Outer terrain must face upward'
    bvh=BVHTree.FromPolygons([Vector(p) for p in vs],fs)
    # River ribbons follow the extended bends; water does not terminate at the old plane.
    water=bpy.data.materials.get('City/water') or B.M['water']
    for line,gate in zip(river_lines,plan['watergates']):
        v=[];f=[]
        for a,b in zip(line,line[1:]):
            length=math.dist(a,b);nx,ny=-(b[1]-a[1])/length,(b[0]-a[0])/length
            for i in range(max(2,math.ceil(length/8))):
                t=i/max(2,math.ceil(length/8));cx=a[0]+(b[0]-a[0])*t;cy=a[1]+(b[1]-a[1])*t
                width=21+3*smooth(math.dist((cx,cy),line[0])/45)
                v.extend([(cx+nx*width,cy+ny*width,-3.47),(cx-nx*width,cy-ny*width,-3.47)])
        for i in range(len(v)//2-1):f.append((2*i,2*i+1,2*i+3,2*i+2))
        B.mesh('RIVER/'+gate['id']+'/Continuation',v,f,water,'Outer_Landscape','none')
    materials={name:bpy.data.materials.get('City/'+name) for name in ['stone','marble','marbleLight','bank','plaster','plasterWarm','plasterPale','tile','tileLight','wood','woodLight','shadow','iron','red','gold','water','ground','road','leaf','leafDark','bark','pot','hill']}
    assert all(materials.values()),'Existing city palette missing'
    families=[_cypress_proto(materials,land),_pine_proto(materials,land)]
    planted=[]
    for group in range(44):
        k=rng.randrange(count);d=rng.uniform(20,150);p=ring[k];n=normals[k];cx,cy=p[0]+n[0]*d,p[1]+n[1]*d
        for j in range(rng.randint(4,8)):
            x,y=cx+rng.uniform(-17,17),cy+rng.uniform(-17,17)
            if river_distance(x,y)<34:continue
            hit,normal,face,dist=bvh.ray_cast(Vector((x,y,300)),Vector((0,0,-1)))
            if hit is None or normal.z<.72:continue
            scale=rng.uniform(.82,1.30);family=families[(group+j)%2];angle=rng.uniform(0,T);prefix=f'OUTER_GROVE/{group}_{j}/'
            for part in family:
                obj=bpy.data.objects.new(f'OUTER_GROVE/{group}_{j}/'+part.data.materials[0].name,part.data);land.objects.link(obj)
                obj.location=(x,y,hit.z-.025);obj.rotation_euler.z=angle;obj.scale=(scale,scale,scale)
                obj['semantic']='landscape/outer_grove';obj['collision']='none';obj['soil_contact_z']=hit.z
            planted.append({'position':[x,y,hit.z],'scale':scale,'prefix':prefix,'support':'LANDSCAPE/Continuous outer hills'})
    for family in families:
        for obj in family:bpy.data.objects.remove(obj,do_unlink=True)
    # Complete small villa masses extend the roof fabric into the outer landscape.
    villas=[];prototype=_house_proto(1,13.4,11.3,2,materials,land)
    bpy.context.view_layer.update()
    bounds=[o.matrix_world@Vector(v) for o in prototype for v in o.bound_box]
    terrace_w=2*max(abs(v.x) for v in bounds)+1.2;terrace_d=2*max(abs(v.y) for v in bounds)+1.2
    for k in range(34):
        i=(k*37+24)%count;d=45+(k%4)*22;p=ring[i];n=normals[i];x,y=p[0]+n[0]*d,p[1]+n[1]*d
        if river_distance(x,y)<46:continue
        hit,normal,face,dist=bvh.ray_cast(Vector((x,y,300)),Vector((0,0,-1)))
        if hit is None or normal.z<.85:continue
        if any(math.dist((x,y),v['position'][:2])<25 for v in villas):continue
        a=math.atan2(n[1],n[0])+math.pi/2;heights=[]
        for u,v in [(-terrace_w/2,-terrace_d/2),(-terrace_w/2,terrace_d/2),(terrace_w/2,-terrace_d/2),(terrace_w/2,terrace_d/2),(0,0)]:
            px=x+u*math.cos(a)-v*math.sin(a);py=y+u*math.sin(a)+v*math.cos(a)
            support=bvh.ray_cast(Vector((px,py,300)),Vector((0,0,-1)))[0]
            if support is not None:heights.append(support.z)
        if len(heights)!=5 or max(heights)-min(heights)>5:continue
        z=max(heights)+.15;bottom=min(heights)-.35
        B.box('OUTER_VILLA/Stone terrace',(x,y,(z+bottom)/2),(terrace_w,terrace_d,z-bottom),'stone',a,'Outer_Landscape')
        for part in prototype:
            obj=bpy.data.objects.new(f'OUTER_VILLA/{k}/'+part.data.materials[0].name,part.data);land.objects.link(obj)
            obj.location=(x,y,z);obj.rotation_euler.z=a;obj['semantic']='landscape/outer_villa';obj['collision']='solid'
        villas.append({'position':[x,y,z],'rotation':a,'terrace':[terrace_w,terrace_d],'foundationBase':bottom,'terrainSupportHeights':heights})
    for obj in prototype:bpy.data.objects.remove(obj,do_unlink=True)
    # Planting must stay outside complete buildings and their stone terraces.
    rejected=[p for p in planted if any(math.dist(p['position'][:2],v['position'][:2])<max(v['terrace'])/2+5*p['scale'] for v in villas)]
    for p in rejected:
        for obj in list(land.objects):
            if obj.name.startswith(p['prefix']):bpy.data.objects.remove(obj,do_unlink=True)
    planted=[p for p in planted if p not in rejected]
    for obj in set(bpy.data.objects)-before:
        if obj.type=='MESH':obj['worldBoundary']=True
    result={'passed':True,'boundarySHA256':hashlib.sha256(raw).hexdigest(),'retiredObjects':retired,
        'wallSpans':len(poly)-len(river_spans),'watchtowers':tower_count,'closedGates':gate_frames,
        'riverGates':len(plan['watergates']),'continuousOuterTerrain':True,'groveTrees':planted,'completeOuterVillas':villas,
        'caveat':'Outer hills and villas are visual world continuation beyond the physically enclosed playable city.'}
    (R/'comparisons/world_boundary_geometry.json').write_text(json.dumps(result,indent=2))
    print('WORLD_BOUNDARY_BUILT',len(planted),len(villas),flush=True)
    return result
