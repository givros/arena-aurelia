"""Independent parcel, route and citywide coverage evidence; no source writes."""
import json,math,hashlib
from pathlib import Path
from collections import Counter
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon,Ellipse,Rectangle,Patch
from district_life_layout import Index,bounds,segment_gap
from street_life_layout import rectangle,overlap,poly_distance,segment_samples
R=Path(__file__).resolve().parents[1]
def gap(a,b):
    if overlap(a,b):return 0
    return min(segment_gap(p,q,s,t) for p,q in zip(a,a[1:]+a[:1]) for s,t in zip(b,b[1:]+b[:1]))
def main():
    raw=(R/'district_life_layout.json').read_bytes();d=json.loads(raw);city=json.loads((R/'city_registry.json').read_text());street=json.loads((R/'street_life_layout.json').read_text())
    source=json.loads((R/'comparisons/district_source_obstacles.json').read_text());index=Index()
    for o in source['obstacles']:index.add(o)
    for p in city['parcels']:
        a=p['rotation'];w,h=p['projection_envelope'];index.add({'id':p['id'],'polygon':rectangle(*p['center'],w,h,a)})
    for o in street['footprint_obstacles']:
        if o['kind']!='existing_house':index.add(o)
    overlaps=[];neighbors=[];oldmin=(999,None,None)
    for i,p in enumerate(d['items']):
        for o in index.nearby(p['center'],15):
            dist=gap(p['polygon'],o['polygon'])
            if dist<oldmin[0]:oldmin=(dist,p['id'],o['id'])
            if dist<.001:overlaps.append([p['id'],o['id']])
            if dist<4:neighbors.append({'new':p['id'],'existing':o['id'],'full_projection_gap':round(dist,4)})
        for q in d['items'][i+1:]:
            if math.dist(p['center'],q['center'])>35:continue
            dist=gap(p['polygon'],q['polygon'])
            if dist<.001:overlaps.append([p['id'],q['id']])
            if dist<4:neighbors.append({'new':p['id'],'newNeighbor':q['id'],'full_projection_gap':round(dist,4)})
    for p in d['items']:index.add(p)
    routes=[]
    for route in d['routes']+d['clear_routes']:
        minimum=(999,None,None)
        width_failures=[]
        for segment_index,(a,b) in enumerate(zip(route['points'],route['points'][1:])):
            width=route.get('existingRouteEntryTransitionWidth',route['width']) if segment_index==0 else route['width']
            for p in segment_samples(a,b,.30):
                if route.get('known_bridge_route') and p[0]<-123 and 97<p[1]<113:continue
                near=index.nearby(p,6)
                m=min(((poly_distance(p,o['polygon']),o['id']) for o in near),default=(10,'open paving'))
                if m[0]<minimum[0]:minimum=(m[0],p,m[1])
                if m[0]+.02<width/2:width_failures.append({'segment':segment_index,'point':p,'distance':m[0],'object':m[1]})
        routes.append({'id':route['id'],'declared_width':route['width'],'existing_route_entry_transition_width':route.get('existingRouteEntryTransitionWidth'),'minimum_source_and_added_projection_distance':round(minimum[0],4),'limiting_point':minimum[1],'limiting_object':minimum[2],'capsule_radius_032_pass':minimum[0]>=.34,'nominal_width_pass':not width_failures,'width_failures':width_failures[:4]})
    spacing=(999,None,None)
    for i,a in enumerate(d['routes']):
        for b in d['routes'][i+1:]:
            dist=min(segment_gap(p,q,s,t) for p,q in zip(a['points'],a['points'][1:]) for s,t in zip(b['points'],b['points'][1:]))
            if dist<spacing[0]:spacing=(dist,a['id'],b['id'])
    report={'layout_sha256':hashlib.sha256(raw).hexdigest(),'counts':d['counts'],'coverage':d['coverage'],'unintended_projection_overlaps':overlaps,'minimum_new_to_existing_projection_gap':oldmin,'neighbor_relations':neighbors,'routes':routes,'minimum_independent_loop_spacing':spacing,
            'ground_source':'Existing plaza0, outer city−0.035; character source grounding remains authoritative.','scope':'Actual source low-geometry hull components at0.2–2.3m, existing full house projections and all added full parcels. Existing bridge deck/ramp route retained from prior actual-controller test. Source integration geometry validation and runtime body traversal remain separate gates.'}
    (R/'comparisons/district_life_layout_audit.json').write_text(json.dumps(report,indent=2))
    colors={'stall':'#b8563c','cargo':'#7c633c','frontage':'#d19a57','infill_shop':'#9b785e','bench':'#568273','brazier':'#e39631'}
    fig,ax=plt.subplots(figsize=(17,17),dpi=160);ax.set_facecolor('#f0ecdd');fig.patch.set_facecolor('#faf7ef')
    ax.add_patch(Rectangle((-201,-231),44,660,fc='#9bbcbc',ec='#678f99',zorder=0))
    ax.add_patch(Ellipse((0,0),212,166,fc='#c6bba2',ec='#7e715a',lw=1.2))
    ax.add_patch(Rectangle((-232.5,98.5),105,13,fc='#aea793',ec='#786f60',lw=.5))
    for p in city['parcels']:
        a=p['rotation'];w,h=p['projection_envelope'];ax.add_patch(Polygon(rectangle(*p['center'],w,h,a),fc='#d2ccc0',ec='#8e877a',lw=.4))
    for p in street['stalls']+street['shops']:ax.add_patch(Polygon(p['polygon'],fc='#d3beb0',ec='#a58a78',lw=.3))
    for o in source['obstacles']:
        if o['id'].startswith(('Block_courtyard','City_cypress','City_pine','Sacred_courtyards','Temple','Basilica')):ax.add_patch(Polygon(o['polygon'],fc='#bdb8a9',ec='#999583',lw=.15,zorder=1))
    for p in d['items']:ax.add_patch(Polygon(p['polygon'],fc=colors[p['kind']],ec='#51483a',lw=.4,zorder=3))
    for r in d['routes']:ax.plot([p[0] for p in r['points']],[p[1] for p in r['points']],lw=.7,color='#527caa',zorder=4)
    for r in d['clear_routes']:ax.plot([p[0] for p in r['points']],[p[1] for p in r['points']],lw=1.8,color='#236456',alpha=.85,zorder=5)
    ax.scatter([p['position'][0] for p in d['anchors']],[p['position'][1] for p in d['anchors']],s=1.9,color='#273639',alpha=.70,zorder=5)
    for key,v in d['regions'].items():
        c=d['coverage'][key];ax.text(v['center'][0],v['center'][1]+16,v['label']+'\n'+str(c['assemblies'])+' trade fronts / '+str(c['patrons'])+' residents',ha='center',va='center',fontsize=7.3,bbox={'boxstyle':'round,pad=.3','fc':'#faf7ee','alpha':.83,'ec':'#a1957d'},zorder=7)
    for key,v in d['cameras'].items():
        if not key.startswith('street_'):continue
        x,y=v['position'][:2];ax.scatter([x],[y],s=23,marker='^',color='#233b69',zorder=8)
    boundary=json.loads((R/'master_world_boundary.json').read_text())
    ax.add_patch(Polygon(boundary['wall']['centerline'],fill=False,ec='#4b4339',lw=3))
    master=json.loads((R/'master_world_layout.json').read_text())
    for p in master['treePlantings']:ax.scatter(*p['position'][:2],s=8,color='#67765a',alpha=.65)
    ax.set(xlim=(-308,351),ylim=(-222,424),xlabel='East / west — metres',ylabel='North / south — metres');ax.set_aspect('equal');ax.grid(ls=':',alpha=.18)
    ax.set_title('Whole arena district — connected streets, commercial courts and residents',fontsize=16,pad=14)
    ax.legend(handles=[Patch(fc=color,label=kind.replace('_',' ').title()) for kind,color in colors.items()],ncol=3,loc='upper center',bbox_to_anchor=(.5,-.05),frameon=False)
    fig.tight_layout();fig.savefig(R/'comparisons/district_life_layout_map.png',bbox_inches='tight');plt.close(fig)
    print(json.dumps({'overlaps':len(overlaps),'body_route_failures':[r['id'] for r in routes if not r['capsule_radius_032_pass']],'nominal_width_failures':[r['id'] for r in routes if not r['nominal_width_pass']],'loop_spacing':spacing,'counts':d['counts']}),flush=True)
if __name__=='__main__':main()
