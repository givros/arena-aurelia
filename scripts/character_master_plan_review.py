"""Independent geometric review of the planned quarter streets, before source QA."""
from pathlib import Path
from collections import defaultdict
import json,hashlib
from shapely.geometry import LineString,Polygon,Point
from shapely.ops import nearest_points
R=Path(__file__).resolve().parents[1];p=R/'master_world_layout.json';raw=p.read_bytes();d=json.loads(raw)
streets={s['id']:LineString(s['points']) for s in d['quarterSpines']};widths={s['id']:s['width'] for s in d['quarterSpines']}
polygons={h['id']:Polygon(h['polygon']) for h in d['housePlacements']};records=[];blocking=[];edges=[];gaps=[]
def merge(intervals):
    out=[]
    for a,b in sorted(intervals):
        if out and a<=out[-1][1]:out[-1][1]=max(b,out[-1][1])
        else:out.append([a,b])
    return out
for ident,line in streets.items():
    assigned=[h for h in d['housePlacements'] if h['quarter']==ident];sides={};quarter_gaps=[]
    for side in [-1,1]:
        intervals=[]
        for h in assigned:
            if h.get('side')!=side:continue
            positions=[line.project(Point(q)) for q in h['polygon']]
            intervals.append([min(positions),max(positions)])
        merged=merge(intervals);coverage=sum(b-a for a,b in merged)/line.length
        cursor=0
        for a,b in merged+[[line.length,line.length]]:
            if a-cursor>=25:
                point=line.interpolate((cursor+a)/2);quarter_gaps.append({'side':side,'length':round(a-cursor,2),'spinePosition':[round(point.x,2),round(point.y,2)]})
            cursor=max(cursor,b)
        sides[str(side)]={'coveredFraction':round(coverage,3),'intervals':merged}
    records.append({'id':ident,'length':round(line.length,2),'width':widths[ident],'houseCount':len(assigned),
        'housesPer100Meters':round(len(assigned)/line.length*100,2),'houseEnvelopeFrontage':sides,'gapsOver25Meters':quarter_gaps})
    for h in d['housePlacements']:
        distance=line.distance(polygons[h['id']])
        if distance<widths[ident]/2-.03:blocking.append({'street':ident,'house':h['id'],'centerlineToHouseEnvelope':round(distance,3),'required':widths[ident]/2})
ids=list(streets);adj={i:set() for i in ids}
for i,a in enumerate(ids):
    for b in ids[i+1:]:
        distance=streets[a].distance(streets[b]);edge_gap=max(0,distance-widths[a]/2-widths[b]/2)
        qa,qb=nearest_points(streets[a],streets[b]);record={'a':a,'b':b,'openGap':round(edge_gap,2),'centerlineGap':round(distance,2),'ends':[[round(qa.x,2),round(qa.y,2)],[round(qb.x,2),round(qb.y,2)]]}
        if edge_gap<=.5:adj[a].add(b);adj[b].add(a);edges.append(record)
        else:gaps.append(record)
remaining=set(ids);components=[]
while remaining:
    seed=min(remaining);found={seed};todo=[seed]
    while todo:
        for neighbor in adj[todo.pop()]-found:found.add(neighbor);todo.append(neighbor)
    remaining-=found;components.append(sorted(found))
bridging=[]
for group in components:
    candidates=[g for g in gaps if (g['a'] in group)!=(g['b'] in group)]
    if candidates:bridging.append(min(candidates,key=lambda g:g['openGap']))
report={'layoutSHA256':hashlib.sha256(raw).hexdigest(),'kind':'plan-review-not-saved-source-validation','sourceChecksPending':True,
    'quarters':records,'totalStreetLength':round(sum(s.length for s in streets.values()),2),'houseCount':len(polygons),
    'houseEnvelopesClearOfReservedStreets':not blocking,'houseCorridorConflicts':blocking,
    'reservedStreetComponents':components,'junctions':edges,'shortestMissingLinksPerComponent':bridging,
    'interpretation':'Disconnected marked corridors can still be traversable across open ground. These gaps identify where an explicit connector, plaza, stair or quay approach should be reserved before infill. House frontage coverage excludes the pending commercial infill and landmarks.'}
(R/'characters/master_pedestrian_review.json').write_text(json.dumps(report,indent=2));print(json.dumps({k:v for k,v in report.items() if k not in ['quarters','junctions']}))
for record in records:print(record['id'],record['houseCount'],record['length'],record['houseEnvelopeFrontage']['-1']['coveredFraction'],record['houseEnvelopeFrontage']['1']['coveredFraction'])
