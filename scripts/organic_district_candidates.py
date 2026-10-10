"""Street-facing infill and small civic courts derived from the organic city."""
import math,json
from pathlib import Path
from shapely.geometry import LineString
from master_world_layout import curve
R=Path(__file__).resolve().parents[1]

INNER_STREETS=[
 ('inner_eastern_lane','eastern_trades',3.2,[[154,-139],[154,-113],[164,-86],[171,-55],[171,-17],[178,18],[174,56],[158,93],[130,117]]),
 ('arena_eastern_backlane','eastern_backstreets',3.0,[[153,-158],[185,-142],[202,-119],[211,-89],[221,-64],[232,-39],[258,-18],[280,3]]),
 ('rear_west_lanes','rear_precinct',3.2,[[-126,76],[-116,98],[-91,108],[-63,106],[-39,117],[-42,146],[-46,174],[-28,194]]),
 ('rear_east_lanes','rear_precinct',3.2,[[124,67],[123,92],[106,110],[108,133],[118,152],[145,157],[154,189]]),
 ('civic_cross_street','temple_civic',3.4,[[-135,183],[-107,189],[-75,191],[-47,187],[-20,200],[14,205],[45,201],[75,195],[111,190],[142,193]]),
 ('east_bank_trade','east_quay',3.0,[[-148,-173],[-145,-140],[-146,-103],[-146,-57],[-147,-18],[-146,25],[-147,66],[-145,89]]),
 ('east_bank_upper','east_quay',3.0,[[-146,121],[-145,153],[-146,194],[-143,232],[-144,271],[-143,308],[-145,349],[-146,392]]),
 ('southern_inside_lane','south_residential',3.0,[[-132,-160],[-103,-163],[-77,-161],[-48,-167],[-17,-173],[15,-174],[42,-161],[76,-155],[108,-158],[139,-170],[164,-179]]),
]
# Keep southern links distinctly bent, joining court mouths without a second
# perfectly mirrored retail grid.
INNER_STREETS += [
 ('southern_outer_lane','south_residential',3.0,[[-130,-204],[-98,-202],[-67,-206],[-34,-211],[0,-217],[32,-212],[66,-207],[106,-209],[142,-203],[173,-186]]),
 ('western_upper_courts','west_quay',3.2,[[-286,192],[-278,232],[-284,269],[-274,309],[-258,347],[-240,379]]),
 ('upper_archive_courts','upper_city',3.2,[[155,255],[181,271],[185,301],[210,321],[240,313],[263,295],[283,283]]),
 ('northern_inner_lane','north_insulae',3.2,[[-49,223],[-41,257],[-29,289],[-10,319],[9,338],[42,349],[71,341]])]
INNER_STREETS += [
 ('inner_east_shop_backs','eastern_trades',3.0,[[145,-86],[141,-49],[144,-12],[146,27],[139,62],[135,86]]),
 ('east_middle_courts','eastern_trades',3.0,[[184,-42],[193,-7],[195,31],[190,65],[184,102],[171,129]]),
 ('civic_scribes_lane','temple_civic',3.0,[[-123,205],[-97,204],[-69,211],[-42,222],[-10,219],[22,217],[50,225],[73,240]]),
 ('archive_lower_cross','north_insulae',3.0,[[56,229],[85,238],[119,248],[152,264],[180,288],[214,282],[246,290]]),
 ('garden_quarter_inner','upper_city',3.0,[[53,276],[63,309],[69,337],[89,362],[117,367],[146,371],[174,369],[198,365]]),
 ('archive_east_courts','upper_city',3.0,[[156,317],[185,327],[211,337],[241,332],[270,312],[291,291],[303,267]]),
 ('southern_gate_west','south_residential',3.0,[[-15,-183],[-33,-189],[-60,-191],[-82,-193],[-108,-200],[-133,-209]]),
 ('southern_gate_east','south_residential',3.0,[[14,-183],[34,-185],[58,-190],[85,-194],[118,-190],[144,-177]])]

def streets():
    return [{'id':sid,'zone':zone,'width':w,'points':curve(pts)} for sid,zone,w,pts in INNER_STREETS]

def infill_candidates(master):
    output=[]
    zones={'southern_west':'south_residential','southern_east':'south_residential','southern_courts':'south_residential','western_quay':'west_quay','eastern_trades':'eastern_trades','eastern_lanes':'eastern_backstreets','aqueduct_courts':'aqueduct_ward','western_civic':'north_insulae','temple_residential':'north_insulae','archive_quarter':'upper_city','upper_courts':'upper_city','northern_hillside':'upper_city'}
    paths=[{'id':s['id'],'zone':zones[s['id']],'width':3.0,'points':s['points']} for s in master['quarterSpines']]+streets()
    for s in paths:
        line=LineString(s['points'])
        for side in [1,-1]:
            at=7.5+(2.6 if side<0 else 0)
            while at<line.length-4:
                p=line.interpolate(at);a=line.interpolate(max(0,at-.7));b=line.interpolate(min(line.length,at+.7));theta=math.atan2(b.y-a.y,b.x-a.x)
                offset=8+s['width']/2+.38;rotation=theta+(math.pi if side<0 else 0)
                output.append((p.x-side*math.sin(theta)*offset,p.y+side*math.cos(theta)*offset,rotation,s['zone'],s['id']))
                at+=14.25+(.8 if int(at)%3==0 else 0)
    # Small, asymmetrical three-sided commercial courts close the gaps between
    # the bent main streets. Their open fourth side provides a visible entrance.
    courts=[(-126,-179,.2,'south_residential'),(-91,-185,-.35,'south_residential'),(-53,-179,.45,'south_residential'),
      (-22,-190,.15,'south_residential'),(27,-183,-.22,'south_residential'),(69,-180,.3,'south_residential'),(112,-185,-.4,'south_residential'),
      (155,18,.1,'eastern_trades'),(160,72,-.2,'eastern_trades'),(195,66,.4,'eastern_trades'),
      (-31,154,.1,'temple_civic'),(51,173,-.4,'temple_civic'),(-109,132,.1,'temple_civic'),(127,178,-.3,'temple_civic'),
      (131,254,.2,'north_insulae'),(184,285,-.15,'upper_city'),(224,301,.3,'upper_city'),(256,319,-.3,'upper_city'),
      (46,369,.15,'upper_city'),(-43,339,.4,'north_insulae'),(-113,217,-.1,'north_insulae'),
      (-260,273,.3,'west_quay'),(-249,348,-.2,'west_quay'),(298,152,.2,'aqueduct_ward')]
    for n,(x,y,rot,zone) in enumerate(courts):
        for a in [0,math.pi/2,math.pi]:
            a+=rot;radius=16.7
            output.append((x+radius*math.cos(a),y+radius*math.sin(a),a-math.pi/2,zone,f'court_{n:02}'))
    return output

def market_candidates(master,parcels):
    result=[]
    # Clear court openings and loading backs receive complete purposeful stalls.
    for n,h in enumerate(parcels):
        a=h['rotation'];ca,sa=math.cos(a),math.sin(a);w,d=h['projection_envelope'];x,y=h['center']
        for u,v in [(-w/2-5.2,-d/2+2),(w/2+5.2,-d/2+2),(0,d/2+9.0)]:
            result.append((x+u*ca-v*sa,y+u*sa+v*ca,a,h,n))
    # The rear festival precinct and quay carry their own close stall groups,
    # separate from quiet residential courts deeper in the city.
    groups=[('rear_precinct',[-70,111],.08),('rear_precinct',[61,111],-.14),
      ('temple_civic',[-112,151],.04),('temple_civic',[123,145],-.25),
      ('east_quay',[-146,-59],math.pi/2),('east_quay',[-145,35],math.pi/2),
      ('west_quay',[-220,65],-math.pi/2),('west_quay',[-220,143],-math.pi/2),
      ('aqueduct_ward',[204,146],math.pi),('aqueduct_ward',[283,147],math.pi),
      ('south_residential',[-114,-198],.25),('south_residential',[127,-186],-.35)]
    for zone,(x,y),a in groups:
        ca,sa=math.cos(a),math.sin(a)
        for n,(u,v) in enumerate([(-11,0),(0,0),(10.1,0),(-6.4,11.2),(5.2,11.9)]):
            result.append((x+u*ca-v*sa,y+u*sa+v*ca,a,{'forced_zone':zone},n))
    return result
