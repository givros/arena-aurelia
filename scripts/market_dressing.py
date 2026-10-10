"""Connected event-market assemblies, with shared geometry and clear public routes."""
import bpy
import math
import random
from mathutils import Vector
from city import CityGeometry, _collection, _material


TAU=math.tau


def _ring(g,mat,center,radius,tube=.05,major=18,minor=6,axis='z'):
    x,y,z=center
    vs=[]
    for i in range(major):
        a=i*TAU/major
        for j in range(minor):
            b=j*TAU/minor
            p=((radius+tube*math.cos(b))*math.cos(a),(radius+tube*math.cos(b))*math.sin(a),tube*math.sin(b))
            if axis=='y':p=(p[0],p[2],p[1])
            if axis=='x':p=(p[2],p[0],p[1])
            vs.append((x+p[0],y+p[1],z+p[2]))
    fs=[(i*minor+j,((i+1)%major)*minor+j,((i+1)%major)*minor+(j+1)%minor,i*minor+(j+1)%minor)
        for i in range(major) for j in range(minor)]
    g.mesh(mat,vs,fs)


def _pot(g,x,y,z,scale=1,kind=0):
    # Wheel-thrown amphora profile with an open mouth, rolled rim and two handles.
    profile=[(0,.14),(.13,.24),(.46,.38),(.74,.36),(.91,.19),(1.16,.14),(1.20,.19),(1.26,.19),(1.26,.12),(1.13,.11)]
    profile=[(h*scale,r*scale) for h,r in profile]
    vs=[(x+r*math.cos(j*TAU/20),y+r*math.sin(j*TAU/20),z+h) for h,r in profile for j in range(20)]
    fs=[]
    for i in range(len(profile)-1):
        for j in range(20):fs.append((i*20+j,i*20+(j+1)%20,(i+1)*20+(j+1)%20,(i+1)*20+j))
    fs.append(tuple(range(19,-1,-1)))
    g.mesh('potDark' if kind%3==0 else 'pot',vs,fs)
    for sign in [-1,1]:
        prev=None
        for k in range(11):
            a=math.pi*k/10
            p=(x+sign*(.17+.30*math.sin(a))*scale,y,z+(.92+.24*math.cos(a))*scale)
            if prev:g.beam('pot',prev,p,.055*scale,6)
            prev=p
    _ring(g,'potRim',(x,y,z+1.225*scale),.174*scale,.028*scale)


def _crate(g,x,y,z,w=1.15,d=.9,h=.9):
    for side in [-1,1]:
        for j in range(4):
            g.box('wood',(x+side*(w/2-.045),y,z+(j+.5)*h/4),(.09,d,h/4-.025))
            g.box('woodLight',(x,y+side*(d/2-.04),z+(j+.5)*h/4),(w,.08,h/4-.025))
    for xx in [-1,1]:
        for yy in [-1,1]:
            g.box('woodLight',(x+xx*(w/2-.09),y+yy*(d/2-.08),z+h/2),(.11,.12,h))
    for j in range(5):
        g.box('wood',(x-w/2+(j+.5)*w/5,y,z+h-.035),(w/5-.018,d,.07))
    g.beam('woodLight',(x-w/2+.05,y-d/2-.02,z+.08),(x+w/2-.05,y-d/2-.02,z+h-.08),.06,4)


def _barrel(g,x,y,z,scale=1):
    profile=[(0,.40),(.12,.43),(.35,.50),(.72,.52),(1.08,.48),(1.24,.40)]
    for j in range(16):
        a0=TAU*j/16+.015
        a1=TAU*(j+1)/16-.015
        vs=[]
        for h,r in profile:
            vs.extend([(x+r*scale*math.cos(a0),y+r*scale*math.sin(a0),z+h*scale),
                       (x+r*scale*math.cos(a1),y+r*scale*math.sin(a1),z+h*scale)])
        g.mesh('woodLight' if j%3 else 'wood',vs,[(i*2,i*2+1,i*2+3,i*2+2) for i in range(len(profile)-1)])
    for h,r in [(.14,.447),(.39,.511),(.96,.50),(1.17,.435)]:
        _ring(g,'iron',(x,y,z+h*scale),r*scale,.037*scale,20,6)
    g.cylinder('wood',(x,y,z+1.22*scale),.385*scale,.04*scale,16)


def _basket(g,x,y,z,r=.36):
    g.cylinder('wicker',(x,y,z+.18),r*.75,.36,12,r)
    for k in range(4):_ring(g,'rope',(x,y,z+.08+k*.08),r*(.8+k*.06),.022,16,5)


def _produce(g,x,y,z,kind=0):
    _basket(g,x,y,z)
    for j in range(8):
        a=j*2.399
        r=.17 if j else 0
        g.cylinder('olive' if kind%2 else 'fruit',(x+r*math.cos(a),y+r*math.sin(a),z+.39+(j%2)*.04),.09,.12,8,.065)


def _table(g,y=-1.5,width=5.2):
    for x in [-width/2+.23,width/2-.23]:
        for yy in [y-.46,y+.46]:
            g.box('wood',(x,yy,.52),(.16,.16,1.04))
        g.box('woodLight',(x,y,.28),(.17,1.15,.12))
    for i in range(6):
        g.box('woodLight',(0,y-.56+(i+.5)*1.12/6,1.05),(width,1.12/6-.015,.11))
    g.box('wood',(0,y,.84),(width,.14,.15))


def _canopy(g,kind):
    W,D=3.65,2.75
    nx,ny=16,12
    vs=[]
    for j in range(ny+1):
        y=-D+2*D*j/ny
        for i in range(nx+1):
            x=-W+2*W*i/nx
            edge=3.45-.30*(1-(x/W)**2)
            z=edge+(4.11-edge)*(1-abs(y)/D)
            vs.append((x,y,z))
    for j in range(ny):
        for i in range(nx):
            q=j*(nx+1)+i
            mat='red' if kind in [0,2] else 'linen'
            if kind==2 and (i//2)%2:mat='linen'
            g.mesh(mat,[vs[q],vs[q+1],vs[q+nx+2],vs[q+nx+1]],[(0,1,2,3),(3,2,1,0)])
    for yy in [-D,D]:
        for i in range(16):
            x0=-W+2*W*i/16
            x1=-W+2*W*(i+1)/16
            z0=3.45-.30*(1-(x0/W)**2)
            z1=3.45-.30*(1-(x1/W)**2)
            g.mesh('goldCloth' if kind==0 else 'linenEdge',[(x0,yy,z0),(x1,yy,z1),(x1,yy,z1-.22),((x0+x1)/2,yy,z0-.34),(x0,yy,z0-.22)],[(0,1,2,3,4),(4,3,2,1,0)])
    # Ropes follow the tensioned edge and terminate at grounded stakes.
    for x in [-W,W]:
        for y in [-D,D]:
            g.beam('rope',(x,y,3.45),(x*1.17,y*1.16,.24),.024,6)
            g.beam('wood',(x*1.17,y*1.16,-.05),(x*1.17,y*1.16,.36),.085,6)
    for xx in [-3.35,3.35]:
        for yy in [-2.45,2.45]:
            g.cylinder('wood',(xx,yy,1.69),.105,3.38,10)
        g.box('woodLight',(xx,0,3.39),(.15,5.3,.16))
        g.cylinder('wood',(xx,0,3.75),.095,.9,10)
    g.box('woodLight',(0,0,4.025),(7,.16,.16))


def _stall(kind,mats,collection):
    g=CityGeometry()
    _canopy(g,kind)
    _table(g)
    # Taut table cover stops above the ground and has a patterned hem.
    if kind==0:
        g.box('red',(0,-1.5,1.12),(5.28,1.2,.03))
        g.box('red',(0,-2.115,.79),(5.28,.025,.67))
        g.box('goldCloth',(0,-2.14,.5),(5.28,.02,.06))
    if kind in [0,2]:
        for i,x in enumerate([-2,-1.25,-.45,.45,1.3,2.1]):
            _pot(g,x,-1.5,1.14,.55+.09*(i%3),i)
    else:
        for i,x in enumerate([-2,-1.1,-.1,.9,1.9]):_produce(g,x,-1.5,1.14,i)
    for x,y,scale in [(-2.6,.9,.85),(2.45,1.6,.68)]:_barrel(g,x,y,0,scale)
    _crate(g,-2.4,-.10,0,.85,.85,.72)
    _crate(g,-2.4,-.10,.72,.72,.67,.65)
    for i in range(4):_pot(g,1.5+(i%2)*.61,.8+(i//2)*.62,0,.68+(i%3)*.12,i)
    # Bench for helpers is beneath the rear edge and leaves the vendor bay clear.
    g.box('woodLight',(0,2.05,.50),(2.4,.48,.13))
    for x in [-.9,.9]:g.box('wood',(x,2.05,.25),(.18,.36,.5))
    return g.objects(f'MarketFamily{kind}',collection,mats,'solid','market/stall')


def _cart(mats,collection):
    g=CityGeometry()
    for i in range(7):g.box('woodLight',(-.95+(i+.5)*1.9/7,0,.86),(1.9/7-.018,3.3,.12))
    for y in [-1.4,1.4]:g.box('wood',(0,y,.65),(2.05,.15,.20))
    for x in [-1.02,1.02]:
        for k in range(3):g.box('woodLight',(x,0,1.05+k*.24),(.09,3.3,.20))
        for y in [-1.4,0,1.4]:g.box('wood',(x,y,1.25),(.11,.13,1.0))
    for k in range(3):g.box('wood',(0,1.60,1.05+k*.24),(2.1,.10,.20))
    g.beam('iron',(-1.36,.2,.68),(1.36,.2,.68),.095,8)
    for x in [-1.30,1.30]:
        _ring(g,'woodLight',(x,.2,.70),.66,.10,24,8,'x')
        _ring(g,'iron',(x,.2,.70),.72,.035,24,6,'x')
        g.beam('wood',(x-.12,.2,.7),(x+.12,.2,.7),.16,10)
        for j in range(10):
            a=TAU*j/10
            g.beam('woodLight',(x,.2,.7),(x,.2+.62*math.cos(a),.70+.62*math.sin(a)),.039,6)
    for x in [-.7,.7]:g.beam('wood',(x,-1.55,.83),(x,-4.0,.62),.083,8)
    _crate(g,0,.6,.96,1.3,1.1,.85)
    _pot(g,-.42,-.76,.95,.9)
    _pot(g,.45,-.68,.95,.85)
    return g.objects('HandcartFamily',collection,mats,'solid','market/cart')


def _clone(assembly,name,x,y,angle,collection):
    out=[]
    for p in assembly:
        o=bpy.data.objects.new(name+'/'+p.data.materials[0].name.split('/')[-1],p.data)
        collection.objects.link(o)
        o.location=(x,y,0)
        o.rotation_euler.z=angle
        o['semantic']='market/'+name
        o['collision']='solid'
        o['prototype']=p['source_component']
        out.append(o)
    return out


def build_market(api=None,spec=None):
    c=_collection('Market_District')
    palette={
        'wood':((.20,.105,.048),.91,0),'woodLight':((.42,.255,.11),.89,0),
        'iron':((.10,.09,.073),.57,.55),'rope':((.50,.39,.23),.98,0),
        'wicker':((.39,.26,.12),.93,0),'linen':((.70,.60,.43),.96,0),
        'linenEdge':((.49,.37,.23),.96,0),'red':((.36,.065,.038),.88,0),
        'goldCloth':((.69,.42,.13),.92,0),'pot':((.49,.22,.10),.90,0),
        'potDark':((.29,.13,.065),.93,0),'potRim':((.64,.34,.16),.84,0),
        'fruit':((.64,.34,.095),.83,0),'olive':((.26,.32,.09),.82,0),
        'stone':((.63,.56,.43),.93,0),'water':((.09,.23,.20),.24,.15)}
    mats={k:_material('Market_'+k,*v) for k,v in palette.items()}
    families=[_stall(i,mats,c) for i in range(3)]
    carts=_cart(mats,c)
    placements=[]
    for deg in [210,225,240,252,288,300,315,330]:
        a=math.radians(deg)
        placements.append((127*math.cos(a),106*math.sin(a),a-math.pi/2))
    for deg in [225,240,252,288,300,315]:
        a=math.radians(deg)
        placements.append((144*math.cos(a),122*math.sin(a),a-math.pi/2))
    for x in [-127,127]:
        for y in [-65,-43,-21,1,23,45,67]:
            placements.append((x,y,-math.pi/2 if x>0 else math.pi/2))
    vendors=[]
    for i,(x,y,a) in enumerate(placements):
        _clone(families[i%3],f'Stall_{i:02}',x,y,a,c)
        # The merchant stands in the open central bay behind the front table.
        vendor=[x-.5*math.sin(a),y+.5*math.cos(a),0]
        customer=[x+4.0*math.sin(a),y-4.0*math.cos(a),0]
        vendors.append({'id':f'Stall_{i:02}','position':vendor,'facing':a,'customer_position':customer})
    cart_positions=[(-45,-126,.8),(49,-128,-.8),(-138,-79,.4),(140,-50,math.pi/2),
                    (-137,34,math.pi/2),(138,61,-math.pi/2)]
    for i,(x,y,a) in enumerate(cart_positions):_clone(carts,f'Cart_{i:02}',x,y,a,c)
    # Basins and grounded plinths punctuate the market courts, away from the main axis.
    misc=CityGeometry()
    for x,y in [(-72,-125),(73,-125),(-137,80),(137,80)]:
        misc.cylinder('stone',(x,y,.18),1.5,.36,20)
        misc.cylinder('stone',(x,y,.74),1.2,.95,20,1.45)
        _ring(misc,'stone',(x,y,1.2),1.42,.15,24,8)
        misc.cylinder('water',(x,y,1.10),1.30,.035,24)
    misc.objects('Market_court_basins',c,mats,'solid','market/basin')
    for assembly in families+[carts]:
        for p in assembly:bpy.data.objects.remove(p,do_unlink=True)
    return {'stall_count':len(placements),'cart_count':len(cart_positions),'vendor_spawns':vendors,
            'clear_avenue':{'x_range':[-8,8],'y_range':[-145,-83]},
            'protected_circulation_ellipse':[114,91],
            'stall_projection_full_dimensions':[8.6,6.5],
            'stalls':[{'id':f'Stall_{i:02}','center':[x,y],'rotation':a,'family':i%3}
                      for i,(x,y,a) in enumerate(placements)]}
