"""Read actual low architecture/tree footprints without changing the source."""
import bpy,json,hashlib
from pathlib import Path
from mathutils import Vector
R=Path(__file__).resolve().parents[1]
def hull(points):
    points=sorted(set((round(x,4),round(y,4)) for x,y in points))
    if len(points)<3:return []
    def cross(o,a,b):return (a[0]-o[0])*(b[1]-o[1])-(a[1]-o[1])*(b[0]-o[0])
    lo=[];hi=[]
    for p in points:
        while len(lo)>=2 and cross(lo[-2],lo[-1],p)<=0:lo.pop()
        lo.append(p)
    for p in reversed(points):
        while len(hi)>=2 and cross(hi[-2],hi[-1],p)<=0:hi.pop()
        hi.append(p)
    return lo[:-1]+hi[:-1]
def main():
    source=R/'Aurelia_Arena.blend';bpy.ops.wm.open_mainfile(filepath=str(source));records=[]
    for o in bpy.context.scene.objects:
        if o.type!='MESH' or o.get('collision','solid') in ['none',False]:continue
        if any(c.name=='Outer_Landscape' for c in o.users_collection):continue
        bounds=[o.matrix_world@Vector(v) for v in o.bound_box]
        lo=[min(v[i] for v in bounds) for i in range(3)];hi=[max(v[i] for v in bounds) for i in range(3)]
        if hi[2]<.20 or lo[2]>2.3 or hi[0]<-310 or lo[0]>350 or hi[1]<-230 or lo[1]>423:continue
        if lo[0]>-108 and hi[0]<108 and lo[1]>-87 and hi[1]<87:continue
        split=max(hi[0]-lo[0],hi[1]-lo[1])>80
        parents=list(range(len(o.data.vertices))) if split else []
        def find(v):
            while parents[v]!=v:parents[v]=parents[parents[v]];v=parents[v]
            return v
        if split:
            for face in o.data.polygons:
                root=find(face.vertices[0])
                for v in face.vertices:parents[find(v)]=root
        components={}
        for f in o.data.polygons:
            vs=[o.matrix_world@o.data.vertices[v].co for v in f.vertices]
            z0=min(v.z for v in vs);z1=max(v.z for v in vs)
            if z0>2.3 or z1<.2:continue
            if abs(z1-z0)<.01:continue
            # Clip each vertical/sloping polygon to pedestrian height.
            for bound,less in [(2.3,True),(.20,False)]:
                clipped=[]
                for a,b in zip(vs,vs[1:]+vs[:1]):
                    ain=a.z<=bound if less else a.z>=bound;bin=b.z<=bound if less else b.z>=bound
                    if ain:clipped.append(a)
                    if ain!=bin:clipped.append(a+(b-a)*((bound-a.z)/(b.z-a.z)))
                vs=clipped
                if not vs:break
            points=components.setdefault(find(f.vertices[0]) if split else 0,[])
            points.extend((v.x,v.y) for v in vs)
        for component,points in components.items():
            polygon=hull(points)
            if len(polygon)>=3:records.append({'id':o.name+('/part'+str(component) if split else ''),'kind':'actual_low_geometry','polygon':polygon,'z':[lo[2],hi[2]]})
    result={'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'height_band':[.2,2.3],'obstacles':records}
    (R/'comparisons/district_source_obstacles.json').write_text(json.dumps(result,indent=2));print('DISTRICT_OBSTACLES',len(records),flush=True)
if __name__=='__main__':main()
