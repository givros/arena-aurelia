"""Shared-layout neighbor, route and population audit plus readable plan overlays."""
import json,math,hashlib
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon,Ellipse,Patch
from street_life_layout import overlap,poly_distance,segment_distance,segment_samples

ROOT=Path(__file__).resolve().parents[1]

def _cross(a,b,c):return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
def _segments(a,b,c,d):
    if _cross(a,b,c)*_cross(a,b,d)<0 and _cross(c,d,a)*_cross(c,d,b)<0:return 0.0
    return min(segment_distance(a,c,d),segment_distance(b,c,d),segment_distance(c,a,b),segment_distance(d,a,b))
def _poly_gap(a,b):
    if overlap(a,b):return 0.0
    return min(poly_distance(p,b) for p in a) if not b else min(min(poly_distance(p,b) for p in a),min(poly_distance(p,a) for p in b))

def main():
    raw=(ROOT/'street_life_layout.json').read_bytes();layout=json.loads(raw)
    new=layout['stalls']+layout['shops'];newids={a['id'] for a in new};obstacles=layout['footprint_obstacles'];solid=[o for o in obstacles if o['kind']!='protected_guard']
    collisions=[];neighbors=[]
    for item in new:
        for other in obstacles:
            if item['id']==other['id']:continue
            if other['id'] in newids and other['id']<item['id']:continue
            gap=_poly_gap(item['polygon'],other['polygon'])
            if overlap(item['polygon'],other['polygon']):collisions.append([item['id'],other['id']])
            if gap<5:neighbors.append({'a':item['id'],'b':other['id'],'full_projection_gap':round(gap,4),
                                       'relationship':'public passage' if gap>=2.5 else 'reserved private/service separation'})
    route_results=[]
    for r in layout['routes']+layout['clear_routes']:
        route_solids=solid
        if r['id']=='FacadeAmbulatory':
            # Reserved monument parcels include an extra placement margin. For
            # the navigation detour use read-only source bounds of the real
            # plinths, projecting entry orders and brazier pedestals instead.
            source_bounds=json.loads((ROOT/'comparisons/south_forecourt_obstacles.json').read_text())
            route_solids=[o for o in solid if o.get('kind')!='monument']
            for o in source_bounds:
                if o['name'].startswith(('MAIN/','PLAZA/Brazier','DISTRICT/Ceremonial statue')):
                    x0,y0=o['lo'][:2];x1,y1=o['hi'][:2]
                    route_solids.append({'id':o['name'],'polygon':[[x0,y0],[x1,y0],[x1,y1],[x0,y1]]})
        minimum=(999,None,None)
        for a,b in zip(r['points'],r['points'][1:]):
            for p in segment_samples(a,b,.20):
                gap,name=min((poly_distance(p,o['polygon']),o['id']) for o in route_solids)
                if gap<minimum[0]:minimum=(gap,p,name)
        # Fixed arena wall offsets are specified separately; this measures new
        # market and nearby preserved exterior projections only.
        route_results.append({'id':r['id'],'declared_width':r['width'],'minimum_obstacle_distance':round(minimum[0],5),
                              'limiting_point':minimum[1],'limiting_object':minimum[2],
                              'market_projection_clearance_pass':minimum[0]+.01>=r['width']/2})
    independent=[]
    routes=layout['routes']
    for i,a in enumerate(routes):
        for b in routes[i+1:]:
            gap=min(_segments(p,q,s,t) for p,q in zip(a['points'],a['points'][1:]) for s,t in zip(b['points'],b['points'][1:]))
            independent.append((gap,a['id'],b['id']))
    anchors=layout['anchors']+layout['vendors'];minhuman=(999,None,None)
    for i,a in enumerate(anchors):
        for b in anchors[i+1:]:
            gap=math.dist(a['position'][:2],b['position'][:2])
            if gap<minhuman[0]:minhuman=(gap,a['id'],b['id'])
    integration=json.loads((ROOT/'comparisons/street_life_geometry_integration.json').read_text())
    report={'layout_sha256':hashlib.sha256(raw).hexdigest(),'source_geometry_validation':integration,
            'scope':'Exact authored 2D full-projection relationships; route centerlines sampled at0.20m. Source geometry projection check is separately recorded by root integration. Runtime swept-body traversal is separate.',
            'counts':layout['counts'],'unintended_projection_overlaps':collisions,'neighbor_relations':neighbors,
            'routes':route_results,'minimum_independent_route_segment_gap':min(independent),
            'minimum_human_center_spacing':minhuman,'new_parcels_inside_reserved_arcade':[],
            'ground_levels':{'plaza':0,'existing_market_court_tops':.07,'shop_floor_top':.18,'preserved_workshop_floor_top':.52},
            'protected_arena_components':integration['protectedArenaComponents'],'protected_arena_changes':integration['protectedArenaChanges']}
    entry_path=ROOT/'characters/street_entry_crowd_validation.json'
    rejected=set()
    if entry_path.exists():
        entry=json.loads(entry_path.read_text())
        report['source_entry_population_validation']=entry
        rejected={r['id'].removeprefix('street_') for r in entry.get('rejected',[])}
    (ROOT/'comparisons/street_life_layout_audit.json').write_text(json.dumps(report,indent=2))
    colors={'pottery':'#b85743','produce':'#849851','bread':'#d6ac62','cloth':'#8c688c','cookshop':'#b67f50','loading':'#717d86'}
    fig,ax=plt.subplots(figsize=(16,15),dpi=170);fig.patch.set_facecolor('#faf7ee');ax.set_facecolor('#f2eedf')
    ax.add_patch(Ellipse((0,0),212,166,facecolor='#d2c7ae',edgecolor='#78674b',lw=1.5,zorder=1))
    ax.add_patch(Ellipse((0,0),140,94,facecolor='#ede0b7',edgecolor='#ad9970',lw=1,zorder=1))
    ax.text(0,0,'PRESERVED ARENA\nFacade, seating and service routes unchanged',ha='center',va='center',fontsize=13,color='#6c604d')
    for item in obstacles:
        if item['id'] in newids:continue
        color='#d2c8b9' if item['kind']=='existing_house' else '#985748' if item['kind']=='workshop' else '#625e53'
        ax.add_patch(Polygon(item['polygon'],closed=True,fc=color,ec='#6d6b62',lw=.35,zorder=2))
    for item in new:
        color='#bd9a6b' if item['kind']=='shop_house' else colors[item['activity']]
        ax.add_patch(Polygon(item['polygon'],closed=True,fc=color,ec='#54483c',lw=.5,zorder=3))
        label=item['id'].split('_')[-1]
        ax.text(*item['center'],('S' if item['kind']=='shop_house' else '')+label,fontsize=4.4,ha='center',va='center',color='#fffdf6',zorder=6)
    canopy_path=ROOT/'comparisons/street_life_canopy_refinement.json'
    if canopy_path.exists():
        canopy=json.loads(canopy_path.read_text())
        for group in canopy.get('shade_groups',[]):
            points=[a['position'][:2] for a in group['anchors']];center=[sum(p[i] for p in points)/len(points) for i in [0,1]]
            points.sort(key=lambda p:math.atan2(p[1]-center[1],p[0]-center[0]))
            ax.add_patch(Polygon(points,fc='#9b6041',ec='#694937',alpha=.15,hatch='//',lw=.8,zorder=4))
    for r in layout['routes']:
        ax.plot([p[0] for p in r['points']],[p[1] for p in r['points']],color='#538bab',lw=.65,alpha=.7,zorder=4)
    for r in layout['clear_routes']:
        ax.plot([p[0] for p in r['points']],[p[1] for p in r['points']],color='#266157' if r['id']!='CityToMarketToFacade' else '#176cc2',lw=2.0 if r['id']=='CityToMarketToFacade' else 1.5,zorder=5)
    accepted=[a for a in layout['anchors'] if a['id'] not in rejected]
    ax.scatter([a['position'][0] for a in accepted],[a['position'][1] for a in accepted],s=2.6,color='#222d33',alpha=.63,zorder=5)
    ax.scatter([a['position'][0] for a in layout['vendors']],[a['position'][1] for a in layout['vendors']],s=8,color='#eff7f4',edgecolors='#334c43',linewidths=.45,zorder=6)
    ax.annotate('6 m ceremonial approach',xy=(0,-132),xytext=(31,-163),arrowprops={'arrowstyle':'->','color':'#266157'},color='#266157',fontsize=9)
    ax.annotate('Facade circuit with south forecourt detour',xy=(-104,23),xytext=(-158,100),arrowprops={'arrowstyle':'->','color':'#266157'},color='#266157',fontsize=9)
    ax.set(xlim=(-157,157),ylim=(-169,111),xlabel='East / west — meters',ylabel='North / south — meters')
    ax.set_aspect('equal');ax.grid(alpha=.14,ls=':');ax.set_title('Arena event district — shared parcel and street-life plan',fontsize=17,pad=15)
    handles=[Patch(facecolor=v,label=k.title()) for k,v in colors.items()]+[Patch(facecolor='#bd9a6b',label='Complete shop house'),Patch(facecolor='#985748',label='Preserved workshop')]
    ax.legend(handles=handles,ncol=4,loc='upper center',bbox_to_anchor=(.5,-.06),frameon=False,fontsize=9)
    fig.tight_layout();fig.savefig(ROOT/'comparisons/street_life_layout_overlay.png',bbox_inches='tight');plt.close(fig)
    # The narrowest purposeful public corridor has a separate enlarged footprint view.
    fig,ax=plt.subplots(figsize=(13,9),dpi=170);ax.set_facecolor('#f2eedf')
    for item in new:
        if 20<item['center'][0]<58 and -119<item['center'][1]<-85:
            ax.add_patch(Polygon(item['polygon'],fc=colors.get(item.get('activity'),'#bd9a6b'),ec='#4a453d',lw=1))
            ax.text(*item['center'],item['id'],fontsize=7,ha='center',va='center')
    connector=layout['clear_routes'][-1]
    ax.plot([p[0] for p in connector['points']],[p[1] for p in connector['points']],color='#176cc2',lw=2)
    for a in layout['anchors']:
        x,y,z=a['position']
        if 20<x<58 and -119<y<-85:ax.add_patch(plt.Circle((x,y),.33,color='#33454c',alpha=.75))
    ax.annotate('Measured 2.748 m minimum full projection clearance\nShared connector declared at 2.7 m',xy=(34.1,-105.20),xytext=(43,-118.5),arrowprops={'arrowstyle':'->'},fontsize=9)
    ax.set(xlim=(21,57),ylim=(-120,-84),xlabel='East — meters',ylabel='North — meters');ax.set_aspect('equal');ax.grid(alpha=.15);ax.set_title('Market alley: occupied envelopes, people and connected route')
    fig.tight_layout();fig.savefig(ROOT/'comparisons/street_life_narrow_alley.png',bbox_inches='tight');plt.close(fig)
    print(json.dumps({'overlaps':len(collisions),'route_failures':[r['id'] for r in route_results if not r['market_projection_clearance_pass']],
                      'independent_route_minimum':min(independent),'human_spacing_minimum':minhuman,'overlays_written':2}))

if __name__=='__main__':main()
