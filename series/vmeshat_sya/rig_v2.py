#!/usr/bin/env python3
"""Hand-drawn, manually keyframed 2D character rig for «Вмешаться».

The source shapes are SVG paths, not images and not 3D models.  A continuous
front-to-profile morph is drawn for the head and torso.  Two-link inverse
kinematics keeps elbows/knees attached to their respective limb segments.
Coordinates are in a 760-unit tall character space, with y=0 at the floor.
"""
from __future__ import annotations
import math


def clamp(x, lo=0., hi=1.): return max(lo, min(hi, x))
def lerp(a,b,t): return a + (b-a)*t
def xy(a,b,t): return (lerp(a[0],b[0],t),lerp(a[1],b[1],t))
def fmt(x): return f'{x:.2f}'

INK = '#243842'
DEFS = '''<defs>
  <linearGradient id="v2skin" x1="0" y1="0" x2=".9" y2=".65"><stop stop-color="#efc1a4"/><stop offset=".64" stop-color="#d7997f"/><stop offset="1" stop-color="#bb796c"/></linearGradient>
  <linearGradient id="v2hair" x1="0" y1="0" x2=".85" y2="1"><stop stop-color="#f5d574"/><stop offset=".58" stop-color="#e5b94f"/><stop offset="1" stop-color="#bd873b"/></linearGradient>
  <linearGradient id="v2hood" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#50baa9"/><stop offset=".52" stop-color="#258e87"/><stop offset="1" stop-color="#176b6c"/></linearGradient>
  <linearGradient id="v2sleeve" x1="0" y1="0" x2="1" y2=".7"><stop stop-color="#48aa9f"/><stop offset="1" stop-color="#1d7777"/></linearGradient>
  <linearGradient id="v2pants" x1="0" y1="0" x2="1" y2=".25"><stop stop-color="#364657"/><stop offset=".5" stop-color="#243547"/><stop offset="1" stop-color="#18293b"/></linearGradient>
  <linearGradient id="v2shoe" x1="0" y1="0" x2="0" y2="1"><stop stop-color="#eef0e9"/><stop offset="1" stop-color="#a7b6b9"/></linearGradient>
  <linearGradient id="v2shirt" x1="0" y1="0" x2="1" y2=".7"><stop stop-color="#55515c"/><stop offset="1" stop-color="#292f38"/></linearGradient>
  <linearGradient id="v2wom" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#c98b7d"/><stop offset="1" stop-color="#975f5c"/></linearGradient>
  <linearGradient id="v2dad" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#8f6668"/><stop offset="1" stop-color="#5b454e"/></linearGradient>
  <linearGradient id="v2uncle" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#9c9d84"/><stop offset="1" stop-color="#596c66"/></linearGradient>
</defs>'''


def bone(a, b, length1, length2, side=1):
    """Solve a bounded 2-bone chain; return (elbow, reachable wrist).

    side=+1/-1 chooses the projected plane of the bend.  Clamping a target
    that is out of reach is important: it prevents detached, stretching arms.
    """
    dx,dy=b[0]-a[0],b[1]-a[1]
    dist=math.hypot(dx,dy)
    ux,uy=(dx/dist,dy/dist) if dist>1e-8 else (0.,1.)
    d=clamp(dist,abs(length1-length2)+.01,length1+length2-.01)
    target=(a[0]+ux*d,a[1]+uy*d)
    along=(length1*length1-length2*length2+d*d)/(2*d)
    height=math.sqrt(max(0,length1*length1-along*along))
    elbow=(a[0]+ux*along-uy*height*side,a[1]+uy*along+ux*height*side)
    return elbow,target


def normal(a,b):
    dx,dy=b[0]-a[0],b[1]-a[1]; d=math.hypot(dx,dy) or 1
    return (-dy/d,dx/d)


def limb(a,e,b,w0,w1,w2,fill,stroke=INK, shade=True):
    """Single smooth outline through the elbow/knee; no overlapping tube caps."""
    n1=normal(a,e); n2=normal(e,b)
    nav=(n1[0]+n2[0],n1[1]+n2[1]); nd=math.hypot(*nav) or 1
    nav=(nav[0]/nd,nav[1]/nd)
    def off(p,v,d): return (p[0]+v[0]*d,p[1]+v[1]*d)
    a1=off(a,n1,w0/2); a2=off(a,n1,-w0/2)
    e1=off(e,nav,w1/2); e2=off(e,nav,-w1/2)
    b1=off(b,n2,w2/2); b2=off(b,n2,-w2/2)
    # The softened corner follows both bones without shortening the anatomy.
    pre1=xy(a1,e1,.82);post1=xy(e1,b1,.18)
    pre2=xy(b2,e2,.82);post2=xy(e2,a2,.18)
    q=lambda p:f'{fmt(p[0])} {fmt(p[1])}'
    # Rounded shoulder cap follows the arm, rather than ending in a flat seam.
    ux,uy=e[0]-a[0],e[1]-a[1]
    d0=math.hypot(ux,uy) or 1
    cap=(a[0]-ux/d0*w0*.50,a[1]-uy/d0*w0*.50)
    d=(f'M {q(a1)} L {q(pre1)} Q {q(e1)} {q(post1)} L {q(b1)} '
       f'Q {q(b)} {q(b2)} L {q(pre2)} Q {q(e2)} {q(post2)} L {q(a2)} Q {q(cap)} {q(a1)} Z')
    out=[f'<path d="{d}" fill="{fill}" stroke="{stroke}" stroke-width="2.4" stroke-linejoin="round"/>']
    if shade:
        # A restrained painted highlight, rather than cylindrical segment bands.
        c0=off(xy(a,e,.13),n1,w0*.22);c1=off(xy(a,e,.78),n1,w1*.20)
        out.append(f'<path d="M{q(c0)} Q{q(c1)} {q(off(e,nav,w1*.22))}" fill="none" stroke="#e8fff6" stroke-opacity=".13" stroke-width="3" stroke-linecap="round"/>')
    return ''.join(out)


def cuff(wrist,elbow,fill='url(#v2sleeve)',border='#24595a'):
    dx,dy=wrist[0]-elbow[0],wrist[1]-elbow[1]
    angle=math.degrees(math.atan2(dy,dx))-90
    return (f'<g transform="translate({fmt(wrist[0])} {fmt(wrist[1])}) rotate({fmt(angle)})">'
      f'<path d="M-15 -14 Q0 -10 15 -14 L14 2 Q0 5 -14 2Z" fill="{fill}" stroke="{border}" stroke-width="2"/>'
      '<path d="M-12 -9 Q0 -5 12 -9" fill="none" stroke="#c4e8df" opacity=".26" stroke-width="1.5"/></g>')


def hand(wrist,elbow,kind='relaxed',mirror=False,skin='url(#v2skin)'):
    """Wrist-attached, separate drawings for relaxed, open, gripping and fist hands."""
    dx,dy=wrist[0]-elbow[0],wrist[1]-elbow[1]
    angle=math.degrees(math.atan2(dy,dx))-90
    m=-1 if mirror else 1
    start=f'<g transform="translate({fmt(wrist[0])} {fmt(wrist[1])}) rotate({fmt(angle)}) scale({m} 1)" stroke-linejoin="round" stroke-linecap="round">'
    if kind=='fist':
        p=(f'<path d="M-12 -1 C-15 2 -16 8 -15 14 L-12 23 Q-9 28 -3 28 L8 27 Q14 25 15 19 L16 9 Q16 3 11 0Z" fill="{skin}" stroke="#75554e" stroke-width="1.8"/>'
           '<path d="M-9 9 Q-5 7 -3 10 M-3 8 Q1 6 3 9 M3 8 Q7 7 9 10 M-10 18 Q-3 15 3 17 Q6 19 4 22" fill="none" stroke="#ad7567" stroke-width="1.3"/>')
    elif kind=='grip':
        p=(f'<path d="M-11 -1 Q-15 3 -15 10 L-13 20 Q-10 27 -3 27 L8 25 Q14 22 14 16 L12 5 Q10 0 7 -1Z" fill="{skin}" stroke="#75554e" stroke-width="1.8"/>'
           '<path d="M-9 9 Q-5 6 -1 9 M-8 14 Q-3 11 1 14 M-6 19 Q-1 16 3 19 M4 8 Q10 9 10 14" fill="none" stroke="#a87165" stroke-width="1.35"/>')
    elif kind=='open':
        p=(f'<path d="M-10 -1 C-13 3 -14 8 -15 13 L-19 22 Q-20 25 -18 26 Q-16 27 -14 24 L-10 18 L-12 32 Q-12 35 -10 35 Q-8 35 -7 32 L-5 22 L-5 36 Q-5 39 -3 39 Q0 39 0 36 L1 23 L2 35 Q2 38 4 38 Q7 37 7 34 L7 21 L9 31 Q10 34 12 33 Q14 32 13 29 L13 15 Q12 8 10 3 L9 -1Z" fill="{skin}" stroke="#75554e" stroke-width="1.7"/>'
           '<path d="M-6 19 L-5 25 M0 20 L0 26 M6 19 L7 24" fill="none" stroke="#b17c70" stroke-width="1.05"/>')
    else:
        p=(f'<path d="M-10 -1 Q-13 4 -13 10 L-12 22 Q-11 29 -9 33 Q-8 35 -6 34 Q-5 33 -6 30 L-7 21 L-4 34 Q-3 37 -1 36 Q1 35 0 32 L-2 20 L2 32 Q3 35 5 34 Q7 33 6 30 L3 18 L8 28 Q9 30 11 29 Q12 28 11 25 L7 12 Q11 13 14 19 Q16 21 18 19 Q19 17 17 14 L12 5 Q10 1 8 -1Z" fill="{skin}" stroke="#75554e" stroke-width="1.7"/>'
           '<path d="M-7 20 L-5 25 M-2 20 L0 25 M3 18 L5 23" fill="none" stroke="#ae7568" stroke-width="1.1"/>')
    return start+p+'</g>'


def shoe(ankle,view=0,side=1,angle=0):
    # A real shoe silhouette with its own sole; profile toes project forward.
    rear=lerp(-20,-19,view); front=lerp(22,36,view)
    return (f'<g transform="translate({fmt(ankle[0])} {fmt(ankle[1])}) rotate({fmt(angle)})">'
      f'<path d="M-16 -8 Q-14 -14 -7 -14 L10 -12 Q16 -10 20 -5 L{fmt(front)} 3 Q{fmt(front+4)} 7 {fmt(front+3)} 12 Q{fmt(front+1)} 16 {fmt(front-4)} 17 L{fmt(rear+2)} 17 Q{fmt(rear-3)} 15 {fmt(rear-2)} 10 L-20 3Z" fill="url(#v2shoe)" stroke="#607078" stroke-width="2.1"/>'
      f'<path d="M{fmt(rear-1)} 10 Q0 14 {fmt(front+3)} 10 L{fmt(front+3)} 14 Q{fmt(front-3)} 19 1 19 L{fmt(rear+2)} 17 Q{fmt(rear-3)} 15 {fmt(rear-1)} 10Z" fill="#e5e9e5" stroke="#77878a" stroke-width="1.2"/>'
      '<path d="M1 -5 L10 -3 M-3 -1 L8 1" stroke="#8d9b9c" stroke-width="1.3" stroke-linecap="round"/></g>')


def morph_path(commands_front, commands_side, u):
    pieces=[]
    for (op,aa),(op2,bb) in zip(commands_front,commands_side):
        assert op==op2 and len(aa)==len(bb)
        pieces.append(op+' '.join(fmt(lerp(a,b,u)) for a,b in zip(aa,bb)))
    return ' '.join(pieces)


FACE_FRONT=[('M',[-40,-61]),('C',[-54,-53,-58,-34,-57,-9]),('C',[-57,17,-48,45,-28,59]),('C',[-18,66,-7,70,0,70]),('C',[8,70,19,66,29,59]),('C',[43,49,51,33,54,20]),('C',[56,13,56,7,56,2]),('C',[56,-2,56,-5,56,-9]),('C',[56,-22,54,-34,50,-43]),('C',[48,-51,45,-58,40,-61]),('C',[18,-75,-18,-75,-40,-61]),('Z',[])]
FACE_SIDE=[('M',[-38,-61]),('C',[-59,-52,-60,-30,-57,-8]),('C',[-56,20,-47,50,-29,61]),('C',[-17,69,-7,72,2,71]),('C',[14,70,27,65,34,57]),('C',[40,51,39,44,42,39]),('C',[46,36,47,32,44,27]),('C',[43,25,57,22,58,18]),('C',[59,15,48,8,46,-4]),('C',[46,-27,39,-53,30,-61]),('C',[12,-75,-18,-75,-38,-61]),('Z',[])]
HAIR_FRONT=[('M',[-53,-25]),('C',[-62,-39,-65,-62,-56,-79]),('C',[-48,-96,-32,-102,-19,-103]),('C',[-3,-111,14,-108,21,-104]),('C',[42,-104,56,-92,58,-76]),('C',[64,-56,58,-38,51,-26]),('L',[47,-56]),('C',[32,-65,19,-62,9,-68]),('C',[-2,-64,-14,-68,-24,-64]),('C',[-35,-60,-44,-57,-48,-43]),('Z',[])]
HAIR_SIDE=[('M',[-52,-24]),('C',[-61,-39,-65,-63,-57,-79]),('C',[-49,-97,-34,-104,-19,-104]),('C',[-2,-112,13,-108,21,-104]),('C',[39,-101,48,-90,47,-75]),('C',[48,-65,42,-51,35,-44]),('L',[32,-59]),('C',[20,-64,9,-62,-2,-68]),('C',[-12,-62,-23,-66,-32,-60]),('C',[-39,-54,-45,-45,-47,-34]),('Z',[])]
BEARD_FRONT=[('M',[-49,4]),('C',[-50,29,-40,52,-26,62]),('C',[-15,72,-5,75,0,75]),('C',[7,75,19,71,29,61]),('C',[42,49,50,28,49,4]),('L',[42,3]),('C',[40,18,31,25,22,26]),('C',[13,18,6,20,0,22]),('C',[-7,19,-14,18,-22,26]),('C',[-32,25,-41,18,-42,3]),('Z',[])]
BEARD_SIDE=[('M',[-51,5]),('C',[-53,30,-42,52,-27,64]),('C',[-15,72,-4,76,2,75]),('C',[12,74,27,68,34,58]),('C',[40,52,41,43,42,35]),('L',[36,29]),('C',[31,30,26,27,23,26]),('C',[16,22,11,21,8,22]),('C',[1,21,-5,19,-12,24]),('C',[-23,25,-35,17,-42,3]),('Z',[])]


def head(role='hero',view=0,anger=0,worry=0,t=0,talk=0,tilt=0):
    v=clamp(view); hero=role in ('hero','child'); female=role in ('woman','mom')
    hair='url(#v2hair)' if hero else ('#523d42' if female else '#29333e')
    edge='#aa7b3c' if hero else '#202e38'
    blink=max(0,1-abs((t+(1.1 if female else 0))%4.6-.12)/.11)
    q=[f'<g transform="translate(0 -661) rotate({fmt(tilt)})">']
    # Back hair is a separate layer for the women, so a side turn remains readable.
    if female:
        q.append('<path d="M-48 -68 Q-68 -42 -60 13 L-64 64 Q-48 79 -29 71 L-27 -18 L35 -27 L43 68 Q58 73 63 60 L57 -4 Q62 -61 35 -81Z" fill="#47363e" stroke="#302f39" stroke-width="2.2"/>')
    earx=lerp(-52,-39,v)
    q.append(f'<path d="M{fmt(earx+3)} -22 C{fmt(earx-15)} -27 {fmt(earx-18)} -4 {fmt(earx-5)} 8 Q{fmt(earx+2)} 12 {fmt(earx+5)} 5Z" fill="url(#v2skin)" stroke="#8f655b" stroke-width="2"/>')
    if v<.83:
        q.append(f'<path d="M45 -22 C60 -26 66 -6 54 6 L47 8Z" fill="url(#v2skin)" stroke="#8f655b" stroke-width="2" opacity="{fmt(1-v/.83)}"/>')
    q.append(f'<path d="{morph_path(FACE_FRONT,FACE_SIDE,v)}" fill="url(#v2skin)" stroke="#815c54" stroke-width="2.2"/>')
    q.append(f'<path d="M{fmt(lerp(-43,-47,v))} -17 Q{fmt(lerp(-46,-51,v))} 23 {fmt(lerp(-23,-27,v))} 54 Q{fmt(lerp(-32,-39,v))} 30 {fmt(lerp(-34,-41,v))} -10Z" fill="#a76460" opacity=".12"/>')
    if female:
        q.append(f'<path d="{morph_path(HAIR_FRONT,HAIR_SIDE,v)}" fill="{hair}" stroke="{edge}" stroke-width="2.2"/>')
        q.append('<path d="M-44 -74 Q-26 -94 -8 -92 M7 -98 Q26 -99 41 -85" fill="none" stroke="#9e7770" stroke-width="2" opacity=".4"/>')
    else:
        q.append(f'<path d="{morph_path(HAIR_FRONT,HAIR_SIDE,v)}" fill="{hair}" stroke="{edge}" stroke-width="2.3"/>')
        hl='#fff0bd' if hero else '#71818a'
        q.append(f'<path d="M-45 -78 Q-29 -94 -10 -96 M2 -99 Q23 -103 39 -88" fill="none" stroke="{hl}" stroke-width="2.3" stroke-linecap="round" opacity=".54"/>')
    # Brows: anger lowers the inside corner; concern raises it.
    leftx=lerp(-24,12,v);rightx=lerp(23,28,v)
    # Keep the far eye legible through the three-quarter view; hide it only
    # as the nose reaches profile, instead of leaving a ghost eye in the face.
    vanish=clamp((v-.73)/.24)
    faropacity=1-vanish*vanish*(3-2*vanish)
    eyeh=max(.12,1-.93*blink)
    farwidth=lerp(1,.40,v)
    browinner=7.0*anger-4.5*worry
    browouter=-3.0*anger+1.3*worry
    def eye(cx,op=1,width=1,near=False):
        # Front-facing brows converge at the bridge. The visible brow in
        # profile slopes towards the projecting nose instead.
        side_turn=clamp((v-.40)/.45);side_turn=side_turn*side_turn*(3-2*side_turn)
        start=lerp(browinner,browouter,side_turn) if near else browouter
        end=lerp(browouter,browinner,side_turn) if near else browinner
        brow=(f'<path d="M-13 {fmt(-26+start)} Q-2 {fmt(-30+(start+end)*.35)} 11 {fmt(-26+end)}" fill="none" stroke="#473d3a" stroke-width="3.2" stroke-linecap="round"/>')
        irisx=lerp(1,3,v)
        return (f'<g transform="translate({fmt(cx)} 0) scale({fmt(width)} 1)" opacity="{fmt(op)}">'+brow+
          f'<g transform="translate(0 -9) scale(1 {fmt(eyeh)}) translate(0 9)">'
          '<path d="M-13 -9 Q-2 -17 11 -9 Q0 -2 -13 -9Z" fill="#f8f4e9" stroke="#66544d" stroke-width="1.45"/>'
          f'<circle cx="{fmt(irisx)}" cy="-9" r="4.6" fill="#405f5d"/><circle cx="{fmt(irisx+1)}" cy="-10.5" r="1.25" fill="#fff"/></g></g>')
    q.append(eye(leftx,faropacity,farwidth))
    q.append(eye(rightx,1,lerp(1,.87,v),True))
    nose_x=lerp(0,41,v)
    if v<.88:
        q.append(f'<path d="M{fmt(nose_x)} -4 Q{fmt(nose_x+6)} 8 {fmt(nose_x+3)} 14 Q{fmt(nose_x)} 16 {fmt(nose_x-4)} 13" fill="none" stroke="#ad7568" stroke-width="1.8" opacity="{fmt(1-v*.9)}" stroke-linecap="round"/>')
    else:
        q.append(f'<path d="M{fmt(nose_x-1)} 18 l4 0" stroke="#9f6d61" stroke-width="1.5" stroke-linecap="round"/>')
    if hero and role!='child':
        q.append(f'<path d="{morph_path(BEARD_FRONT,BEARD_SIDE,v)}" fill="url(#v2hair)" stroke="#ad813e" stroke-width="2"/>')
        mx=lerp(0,25,v)
        q.append(f'<path d="M{fmt(mx-19)} 28 Q{fmt(mx-10)} 18 {fmt(mx)} 24 Q{fmt(mx+8)} 19 {fmt(mx+17)} 26 Q{fmt(mx+12)} 30 {fmt(mx+5)} 28 L{fmt(mx)} 26 Q{fmt(mx-7)} 30 {fmt(mx-19)} 28Z" fill="#e9bd5b" stroke="#b4893e" stroke-width="1.2"/>')
    else: mx=lerp(0,34,v)
    if talk>.06:
        q.append(f'<ellipse cx="{fmt(mx)}" cy="{fmt(35 if hero else 38)}" rx="{fmt(7-2*v)}" ry="{fmt(1.5+5.5*talk)}" fill="#704349"/><path d="M{fmt(mx-3)} 40 Q{fmt(mx)} 41 {fmt(mx+3)} 40" fill="none" stroke="#df9990" stroke-width="1.2"/>')
    else:
        my=36 if hero else 38
        q.append(f'<path d="M{fmt(mx-8)} {fmt(my)} Q{fmt(mx)} {fmt(my-2.6*anger+2*worry)} {fmt(mx+8)} {fmt(my)}" fill="none" stroke="#80534e" stroke-width="2" stroke-linecap="round"/>')
    q.append(f'<path d="M{fmt(earx-3)} -12 q-5 -7 -6 0 q0 8 6 9" fill="none" stroke="#b77f6e" stroke-width="1.4"/>')
    return ''.join(q)+'</g>'


def torso(role,view):
    v=clamp(view); sx=1-.30*v; shift=9*v
    fill={'hero':'url(#v2hood)','child':'url(#v2hood)','man':'url(#v2shirt)',
          'woman':'url(#v2wom)','mom':'url(#v2wom)','dad':'url(#v2dad)','uncle':'url(#v2uncle)'}.get(role,'url(#v2shirt)')
    z=[f'<g transform="translate({fmt(shift)} 0) scale({fmt(sx)} 1)">']
    # Continuous shoulder-to-waist contour, rounded and fitted, not a square box.
    z.append(f'<path d="M-54 -553 Q-80 -547 -96 -530 Q-106 -518 -103 -495 L-96 -425 Q-95 -379 -91 -344 Q-89 -321 -69 -314 Q0 -303 69 -314 Q89 -321 91 -344 Q95 -379 96 -425 L103 -495 Q106 -518 96 -530 Q80 -547 54 -553Z" fill="{fill}" stroke="#285356" stroke-width="2.5"/>')
    z.append('<path d="M-87 -507 Q-82 -429 -84 -380 Q-83 -335 -64 -321 Q-82 -323 -88 -342 L-94 -461Z" fill="#173b45" opacity=".16"/>')
    z.append('<path d="M80 -508 Q74 -449 77 -390 M-75 -372 Q-79 -347 -72 -332 M64 -372 Q70 -348 64 -335" fill="none" stroke="#dafff0" opacity=".15" stroke-width="2" stroke-linecap="round"/>')
    if role in ('hero','child'):
        z.extend(['<path d="M-60 -549 Q-55 -574 -32 -577 Q0 -584 32 -577 Q55 -574 60 -549 L48 -521 Q0 -507 -48 -521Z" fill="#227b78" stroke="#235b5b" stroke-width="2.5"/>',
          '<path d="M-49 -543 Q0 -557 49 -543 Q37 -512 0 -500 Q-35 -511 -49 -543Z" fill="#174c57"/>',
          '<path d="M-47 -543 Q0 -550 47 -543" fill="none" stroke="#69c4b4" stroke-width="2" opacity=".7"/>',
          '<path d="M-22 -515 Q-20 -490 -18 -458 M22 -515 Q20 -490 18 -458" fill="none" stroke="#cfe6d8" stroke-width="2.3" stroke-linecap="round"/>',
          '<circle cx="-18" cy="-456" r="2.7" fill="#cfe6d8"/><circle cx="18" cy="-456" r="2.7" fill="#cfe6d8"/>',
          '<path d="M-66 -375 Q-46 -385 -33 -381 M66 -375 Q46 -385 33 -381 M-68 -344 Q0 -336 68 -344 M-88 -319 Q0 -306 88 -319" fill="none" stroke="#b1ded1" stroke-width="1.8" opacity=".27"/>'])
    else:
        z.append('<path d="M-45 -548 Q0 -537 45 -548 Q28 -523 0 -519 Q-27 -524 -45 -548Z" fill="#172b35" opacity=".46"/>')
        z.append('<path d="M-73 -331 Q0 -324 73 -331" fill="none" stroke="#e5d8c5" opacity=".15" stroke-width="2"/>')
    return ''.join(z)+'</g>'


def tattoo(elbow,wrist):
    dx=wrist[0]-elbow[0];dy=wrist[1]-elbow[1]
    ang=math.degrees(math.atan2(dy,dx))-90
    cx=(elbow[0]+wrist[0])*.5;cy=(elbow[1]+wrist[1])*.5
    return (f'<g transform="translate({fmt(cx)} {fmt(cy)}) rotate({fmt(ang)})" fill="none" stroke="#35474a" stroke-width="2" stroke-linecap="round" opacity=".85">'
      '<path d="M-10 -29 L0 -20 L10 -29 M-10 -19 L0 -10 L10 -19 M-10 5 Q0 -9 10 5 M-9 15 L0 8 L9 15 M-7 23 L7 23"/><circle cy="-1" r="3"/></g>')


def person(x,ground,scale,role='hero',view=.7,facing=1,t=0,phase=0,walk=0,
           sit=0,pose='idle',gesture=0,anger=0,worry=0,lean=0,head_tilt=0,
           talk=0,kick=0,opacity=1,terrain_slope=0,foot_floor=None):
    """Articulated, original 2D drawing, all joints in local scene coordinates.

    ``view`` is the manually drawn front/profile morph; ``pose`` changes the
    hand-drawn targets, while the joint solver avoids disconnected limbs.
    """
    v=clamp(view);g=clamp(gesture);sit=clamp(sit);kick=clamp(kick)
    step=math.sin(phase)*walk
    bob=(abs(math.sin(phase))*3.5)*walk + math.sin(t*1.8)*1.0*(1-walk)
    ground_pos=ground-bob*scale
    q=[f'<g opacity="{fmt(opacity)}" transform="translate({fmt(x)} {fmt(ground_pos)}) scale({fmt(scale*facing)} {fmt(scale)})">']
    # Foot shadow stays on the actual floor, including on stairs.
    shadow_y=4+bob if foot_floor is None else (foot_floor(x)-ground_pos)/scale+4
    q.append(f'<ellipse cx="5" cy="{fmt(shadow_y)}" rx="80" ry="10" fill="#0c202c" opacity=".20"/>')
    hipspread=lerp(32,12,v)
    legdata=[]
    for side in (-1,1):
        hip=(side*hipspread,-320)
        # A hand-timed contact / passing / swing cycle: the grounded foot
        # travels backwards under the body, and only the recovery foot lifts.
        # This avoids the two shoes sliding back and forth in a sine-wave loop.
        cycle=(phase/(2*math.pi)+(0.5 if side==-1 else 0.))%1.
        if cycle<.58:
            stride=25*(1-2*cycle/.58)
            lift=0.
        else:
            u=(cycle-.58)/.42
            eased=u*u*(3-2*u)
            stride=25*(-1+2*eased)
            lift=22*math.sin(math.pi*u)
        stride*=walk;lift*=walk
        foot_x=side*lerp(32,12,v)+stride
        if foot_floor is None:
            foot_delta=terrain_slope*foot_x
        else:
            # Set each planted shoe independently on its own stair tread.
            world_x=x+scale*facing*foot_x
            foot_delta=(foot_floor(world_x)-ground_pos)/scale
        stand_ankle=(foot_x,-18-lift+foot_delta)
        # As a leg rotates into profile its projected bend changes continuously.
        turn=clamp((v-.25)/.65);turn=turn*turn*(3-2*turn)
        knee_side=lerp(1,-1,turn) if side==-1 else -1
        # Extra projected bend is only needed on stairs; a longer standing
        # chain makes both knees bow unnaturally in otherwise neutral poses.
        upper,lower=(157,154) if foot_floor is not None else (153,150)
        knee,ankle=bone(hip,stand_ankle,upper,lower,knee_side)
        # Hand-keyframed sitting: thighs point forward, shins hang down.
        sit_knee=(lerp(side*47,135+side*6,v),lerp(-258,-300,v)+side*3)
        sit_ankle=(lerp(side*44,133+side*5,v)+math.sin(phase+side*.15)*10,lerp(-97,-150,v)+side*4)
        knee=xy(knee,sit_knee,sit);ankle=xy(ankle,sit_ankle,sit)
        if side==1 and kick>0:
            kk,ka=bone(hip,(295,-298),153,150,1)
            knee=xy(knee,kk,kick);ankle=xy(ankle,ka,kick)
        legdata.append((side,hip,knee,ankle))
    # The far leg is painted first; the near leg overlaps naturally in profile.
    for side,hip,knee,ankle in legdata:
        fill='url(#v2pants)'
        q.append(limb(hip,knee,ankle,47,40,31,fill,stroke='#202e3d',shade=False))
        q.append(f'<path d="M{fmt(knee[0]-12)} {fmt(knee[1]-4)} q10 4 21 0 M{fmt(ankle[0]-11)} {fmt(ankle[1]-17)} q10 4 20 0" fill="none" stroke="#8796a1" stroke-opacity=".16" stroke-width="1.5"/>')
        q.append(shoe(ankle,v,side,angle=lerp(-step*3*side,-10 if side==1 else 5,kick if side==1 else 0)))
    # Pelvis hides the top seams of the trouser legs.
    q.append(f'<path d="M{fmt(-66+12*v)} -337 Q0 -328 {fmt(66-12*v)} -337 L{fmt(61-12*v)} -310 Q0 -300 {fmt(-61+12*v)} -310Z" fill="#243547" stroke="#1e2e3d" stroke-width="2"/>')
    q.append(f'<g transform="rotate({fmt(lean)} 0 -320)">')
    shoulder_far=(lerp(-83,25,v),-522)
    shoulder_near=(lerp(83,-37,v),-522)
    # Resting arms counter-swing against the legs, with wrists close to hips.
    fw=(lerp(-103,25,v)-step*36,-323-abs(step)*3)
    nw=(lerp(103,-36,v)+step*36,-323-abs(step)*3)
    fk=nk='relaxed'
    if sit>.01:
        fw=xy(fw,(-72,-510),sit);nw=xy(nw,(72,-510),sit)
        fk=nk='grip'
    if pose=='knock':
        nw=xy(nw,(176,-468),g);nk='fist'
    elif pose=='question':
        nw=xy(nw,(154,-413),g);nk='open'
    elif pose=='warn':
        nw=xy(nw,(150,-439),g);nk='open'
    elif pose=='strike':
        nw=xy(nw,(165,-625),g);nk='fist'
    elif pose=='defend':
        # The near palm shields the face. The far arm remains naturally behind
        # the torso, rather than producing a detached-looking shoulder/hand.
        nw=xy(nw,(88,-570),g);nk='open'
    elif pose=='think':
        nw=xy(nw,(31,-598),g);nk='relaxed'
    elif pose=='mediate':
        fw=xy(fw,(-150,-427),g);nw=xy(nw,(150,-427),g);fk=nk='open'
    elif pose=='argue':
        nw=xy(nw,(148,-423),g);nk='open'
    elif pose=='angry':
        nk='fist';fk='fist'
    # Projected elbow directions move continuously as the torso turns or sits;
    # hard switching them caused a visibly broken arm in early tests.
    turn=clamp((v-.18)/.67);turn=turn*turn*(3-2*turn)
    side_far=lerp(1,-1,sit)
    side_near=lerp(-1,1,turn)
    if pose in ('knock','question','warn','strike','think','mediate','argue'):
        side_near=lerp(side_near,1,g)
    if pose=='mediate':
        side_far=lerp(side_far,-1,g)
    side_near=lerp(side_near,1,sit)
    e_far,fw=bone(shoulder_far,fw,107,104,side_far)
    e_near,nw=bone(shoulder_near,nw,107,104,side_near)
    sleeve='url(#v2sleeve)' if role in ('hero','child') else ('url(#v2skin)' if role=='man' else {'woman':'url(#v2wom)','mom':'url(#v2wom)','dad':'url(#v2dad)','uncle':'url(#v2uncle)'}.get(role,'url(#v2shirt)'))
    bord='#875e56' if role=='man' else '#275b5b'
    def arm_parts(s,e,w,k,mirror=False):
        output=limb(s,e,w,51 if role=='man' else 47,40,28,sleeve,stroke=bord)
        if role=='man':output+=tattoo(e,w)
        else:output+=cuff(w,e,sleeve,bord)
        output+=hand(w,e,k,mirror)
        return output
    q.append(arm_parts(shoulder_far,e_far,fw,fk,True))
    # Neck, torso, head and near arm are separate depth layers.
    q.append('<path d="M-23 -610 L-24 -558 Q-5 -541 0 -541 Q9 -542 24 -558 L23 -610Z" fill="url(#v2skin)" stroke="#8e655c" stroke-width="2"/>')
    q.append(torso(role,v))
    q.append(head(role,v,anger,worry,t,talk,head_tilt))
    q.append(arm_parts(shoulder_near,e_near,nw,nk,False))
    q.append('</g></g>')
    return ''.join(q)
