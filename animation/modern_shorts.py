#!/usr/bin/env python3
"""Original, procedurally keyframed 2D cartoon for a vertical Shorts format.

All scenes, characters and props are hand-authored SVG paths, rasterized by
resvg's vector engine. No photographs, AI images, or animated stills are used.
"""
from __future__ import annotations
import argparse
import math
import subprocess
import tempfile
import wave
from pathlib import Path

import imageio_ffmpeg
import numpy as np
import resvg_py

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'videos' / '06_modern_comic_shorts.mp4'
SOUNDS = ROOT / 'animation' / 'sounds'
W, H = 540, 960
FPS, DURATION = 30, 10
OUTPUT_W, OUTPUT_H = 1080, 1920
FONT_FILES = ['/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
              '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf']


def clamp(v, low=0, high=1): return max(low, min(high, v))
def smooth(a,b,x):
    z=clamp((x-a)/(b-a)); return z*z*(3-2*z)
def mix(a,b,u): return a+(b-a)*u
def pt(a,b,u): return (mix(a[0],b[0],u),mix(a[1],b[1],u))
def n(v): return f'{v:.4f}'

DEFS = '''<defs>
<linearGradient id="sky" x1="0" y1="0" x2="0" y2="1"><stop stop-color="#44586c"/><stop offset="0.55" stop-color="#aab9bb"/><stop offset="1" stop-color="#e0c7a8"/></linearGradient>
<linearGradient id="room" x1="0" x2="1" y1="0" y2="1"><stop stop-color="#c4ceca"/><stop offset="1" stop-color="#758c91"/></linearGradient>
<linearGradient id="roomshade" x1="0" x2="0" y1="0" y2="1"><stop stop-color="#182937" stop-opacity="0"/><stop offset="1" stop-color="#182937" stop-opacity=".43"/></linearGradient>
<linearGradient id="wall" x1="0" x2="1" y1="0" y2="1"><stop stop-color="#f2e9d9"/><stop offset="1" stop-color="#c7c5b9"/></linearGradient>
<linearGradient id="roof" x1="0" x2="1" y1="0" y2="1"><stop stop-color="#465768"/><stop offset="1" stop-color="#253848"/></linearGradient>
<linearGradient id="glass" x1="0" x2="1" y1="0" y2="1"><stop stop-color="#a8d2d3"/><stop offset="1" stop-color="#4a7786"/></linearGradient>
<linearGradient id="hoodie" x1="0" x2="1" y1="0" y2="1"><stop stop-color="#55c0b1"/><stop offset=".55" stop-color="#27988f"/><stop offset="1" stop-color="#1a6e70"/></linearGradient>
<linearGradient id="hooddark" x1="0" x2="1" y1="0" y2="1"><stop stop-color="#288c88"/><stop offset="1" stop-color="#175b61"/></linearGradient>
<linearGradient id="uniform" x1="0" x2="1" y1="0" y2="1"><stop stop-color="#4a607b"/><stop offset="1" stop-color="#263b56"/></linearGradient>
<linearGradient id="pants" x1="0" x2="1" y1="0" y2="0"><stop stop-color="#253648"/><stop offset=".55" stop-color="#3a4d5b"/><stop offset="1" stop-color="#1c2b3c"/></linearGradient>
<linearGradient id="skin" x1="0" x2="1" y1="0" y2=".7"><stop stop-color="#eebc9b"/><stop offset=".65" stop-color="#d9997e"/><stop offset="1" stop-color="#c77f6a"/></linearGradient>
<linearGradient id="skin2" x1="0" x2="1" y1="0" y2=".7"><stop stop-color="#cfa087"/><stop offset=".65" stop-color="#b17b68"/><stop offset="1" stop-color="#966354"/></linearGradient>
<linearGradient id="car" x1="0" x2="0" y1="0" y2="1"><stop stop-color="#f4f7f2"/><stop offset=".55" stop-color="#d8e0dd"/><stop offset="1" stop-color="#a5b7b9"/></linearGradient>
<linearGradient id="road" x1="0" x2="0" y1="0" y2="1"><stop stop-color="#4d5965"/><stop offset="1" stop-color="#263340"/></linearGradient>
<radialGradient id="warmglow"><stop stop-color="#ffe1a1" stop-opacity=".65"/><stop offset="1" stop-color="#ffc080" stop-opacity="0"/></radialGradient>
<radialGradient id="blueglow"><stop stop-color="#38bafa" stop-opacity=".66"/><stop offset="1" stop-color="#38bafa" stop-opacity="0"/></radialGradient>
<radialGradient id="redglow"><stop stop-color="#ff5a72" stop-opacity=".60"/><stop offset="1" stop-color="#ff5a72" stop-opacity="0"/></radialGradient>
<linearGradient id="vig" x1="0" x2="0" y1="0" y2="1"><stop stop-color="#142333" stop-opacity=".30"/><stop offset=".25" stop-color="#142333" stop-opacity="0"/><stop offset=".75" stop-color="#142333" stop-opacity="0"/><stop offset="1" stop-color="#142333" stop-opacity=".42"/></linearGradient>
</defs>'''

INK = '#263342'


def capsule(a,b,w0,w1,fill,stroke=INK,stroke_width=2.6):
    """A tapered arm/leg segment, generated from moving joint coordinates."""
    dx,dy=b[0]-a[0],b[1]-a[1]
    length=math.hypot(dx,dy) or 1
    nx,ny=-dy/length,dx/length
    a1=(a[0]+nx*w0/2,a[1]+ny*w0/2); a2=(a[0]-nx*w0/2,a[1]-ny*w0/2)
    b1=(b[0]+nx*w1/2,b[1]+ny*w1/2); b2=(b[0]-nx*w1/2,b[1]-ny*w1/2)
    return (f'<path d="M {n(a1[0])} {n(a1[1])} Q {n(b1[0])} {n(b1[1])} {n(b1[0])} {n(b1[1])} '
            f'Q {n(b[0]+dx/length*w1*.15)} {n(b[1]+dy/length*w1*.15)} {n(b2[0])} {n(b2[1])} '
            f'L {n(a2[0])} {n(a2[1])} Q {n(a[0]-dx/length*w0*.14)} {n(a[1]-dy/length*w0*.14)} '
            f'{n(a1[0])} {n(a1[1])} Z" fill="{fill}" stroke="{stroke}" stroke-width="{stroke_width}" stroke-linejoin="round"/>')


def arm(shoulder, elbow, wrist, fill):
    """Two overlapping, tapered strokes create one soft, continuously bending sleeve."""
    a=f'M{n(shoulder[0])} {n(shoulder[1])} L{n(elbow[0])} {n(elbow[1])}'
    b=f'M{n(elbow[0])} {n(elbow[1])} L{n(wrist[0])} {n(wrist[1])}'
    common='fill="none" stroke-linecap="round" stroke-linejoin="round"'
    return (f'<path d="{a}" {common} stroke="{INK}" stroke-width="46"/>'
            f'<path d="{b}" {common} stroke="{INK}" stroke-width="38"/>'
            f'<path d="{a}" {common} stroke="{fill}" stroke-width="41"/>'
            f'<path d="{b}" {common} stroke="{fill}" stroke-width="33"/>')


def hand(x,y,angle=0,phone=False,rotation=0,ring=0,skin='skin'):
    """Hand and separately posed prop, with knuckles/fingers drawn on top."""
    a=[f'<g transform="translate({n(x)} {n(y)}) rotate({n(angle)})">',
       '<path d="M -13 -12 Q -17 -8 -15 2 L -11 12 Q -7 18 2 16 L 13 10 Q 19 5 15 -3 L 10 -13 Q 4 -17 -6 -15 Z" fill="url(#skin)" stroke="#664c49" stroke-width="2"/>',
       '<path d="M -8 3 Q -3 6 -1 12 M -3 1 Q 2 4 4 10 M 2 -1 Q 7 2 9 7" fill="none" stroke="#a56457" stroke-width="1.15" stroke-linecap="round"/>',
       '</g>']
    if skin != 'skin':
        a = [fragment.replace('url(#skin)',f'url(#{skin})') for fragment in a]
    if phone:
        a.extend([f'<g transform="translate({n(x+3)} {n(y-10)}) rotate({n(rotation)})">',
                  '<rect x="-13" y="-26" width="26" height="50" rx="6" fill="#172737" stroke="#d3e1de" stroke-width="1.3"/>',
                  '<rect x="-10.4" y="-22.5" width="20.8" height="40.5" rx="3" fill="#4d7986"/>',
                  '<path d="M -8 -20 L 8 -20 L 1 -6 L -8 0Z" fill="#b4e1dc" opacity=".28"/>',
                  '<rect x="-4.5" y="-24" width="9" height="2" rx="1" fill="#e3efed"/>',
                  '<path d="M -13 3 Q -8 0 -7 5 L -7 14 Q -11 18 -14 13Z" fill="#e6aa8f" stroke="#86574f" stroke-width="1"/>',
                  '</g>'])
        if ring>0:
            a.append(f'<g opacity="{n(ring)}" fill="none" stroke="#e6c77b" stroke-linecap="round" stroke-width="2.5">'
                     f'<path d="M {n(x+23)} {n(y-35)} q 9 8 1 16"/><path d="M {n(x+29)} {n(y-41)} q 16 13 2 27"/></g>')
    return ''.join(a)


def head(role='hero', emotion=0, look=0, blink=0, tilt=0, t=0, second=False):
    # A small head turn + changing eyebrows, pupils, eyelids and mouth create acting.
    brow = -5.2*emotion
    eye = max(.08, (1+.25*emotion)*(1-blink*.95))
    mouth_open = 1.2 + 5.5*emotion
    hair = '#27333b' if role=='hero' else '#30363d'
    parts=[f'<g transform="translate(0 -540) rotate({n(tilt)})">',
           # ears and jaw
           '<path d="M-48 -18 C-62 -31 -66 -9 -54 8 Q-51 12 -46 10 M48 -18 C62 -31 66 -9 54 8 Q51 12 46 10" fill="url(#skin)" stroke="#72544e" stroke-width="2.2"/>',
           '<path d="M-50 -55 C-58 -30 -56 2 -48 26 C-42 46 -25 64 -7 70 C 0 72 7 71 13 68 C 31 60 44 43 49 22 C 56 -6 56 -36 47 -58 Q32 -83 0 -84 Q-34 -85 -50 -55Z" fill="url(#skin)" stroke="#71504c" stroke-width="2.4"/>',
           '<path d="M-48 -22 C-50 8 -45 37 -24 55 Q-39 44 -41 19Z" fill="#b56e61" opacity=".21"/>',
           '<path d="M20 -38 Q34 -35 40 -23 Q37 -43 22 -50Z" fill="#ffe0c2" opacity=".25"/>']
    if role=='hero':
        parts.append(f'<path d="M-52 -33 C-61 -44 -63 -60 -57 -76 C-53 -89 -44 -97 -30 -99 C-24 -111 -10 -114 0 -108 C11 -115 24 -111 29 -102 C45 -102 55 -93 57 -80 Q62 -64 51 -36 L45 -58 Q37 -55 30 -64 Q19 -58 10 -67 Q-2 -60 -12 -69 Q-27 -60 -40 -61 L-45 -36Z" fill="{hair}" stroke="#1f2b35" stroke-width="2.5"/>')
        parts.append('<path d="M-42 -83 Q-22 -99 -3 -94 M8 -100 Q27 -103 42 -89" fill="none" stroke="#5f6d6b" stroke-width="2.1" stroke-linecap="round" opacity=".7"/>')
    else:
        parts.append(f'<path d="M-52 -40 Q-60 -66 -48 -79 Q-32 -91 0 -87 Q35 -91 49 -75 Q56 -62 51 -37 L44 -59 Q26 -67 7 -65 Q-18 -59 -43 -62Z" fill="{hair}"/>')
        if second:
            parts.append('<path d="M42 -53 Q64 -46 58 -23 Q68 -10 55 0 L49 -11Z" fill="#30363d"/>')
    # Eyebrows and gaze are independently animated.
    parts.append(f'<path d="M-34 {n(-24+brow)} Q-23 {n(-29+brow)} -11 {n(-23+brow)} M10 {n(-23+brow)} Q22 {n(-29+brow)} 34 {n(-24+brow)}" fill="none" stroke="#423f3d" stroke-width="3.6" stroke-linecap="round"/>')
    if eye < .3:
        parts.append('<path d="M-34 -6 Q-22 -2 -11 -7 M11 -7 Q22 -2 34 -6" fill="none" stroke="#393b3b" stroke-width="2.7" stroke-linecap="round"/>')
    else:
        parts.append(f'<g transform="translate(0 -6) scale(1 {n(eye)}) translate(0 6)">'
                     '<path d="M-34 -6 Q-23 -15 -11 -7 Q-22 1 -34 -6 M11 -7 Q22 -15 34 -6 Q23 1 11 -7" fill="#f7f2e9" stroke="#5c514b" stroke-width="1.5"/>'
                     f'<circle cx="{n(-21+look)}" cy="-6" r="4.7" fill="#384d4c"/><circle cx="{n(22+look)}" cy="-6" r="4.7" fill="#384d4c"/>'
                     f'<circle cx="{n(-20+look)}" cy="-7.5" r="1.3" fill="#fff"/><circle cx="{n(23+look)}" cy="-7.5" r="1.3" fill="#fff"/></g>')
    parts.append('<path d="M1 -3 Q7 10 3 16 Q0 18 -5 15" fill="none" stroke="#a86f5f" stroke-width="2" stroke-linecap="round"/>')
    if role == 'hero' and emotion>.18:
        parts.append(f'<ellipse cx="0" cy="36" rx="8.5" ry="{n(mouth_open)}" fill="#75464a"/>'
                     f'<path d="M-5 {n(36+mouth_open*.45)} Q0 {n(34+mouth_open)} 5 {n(36+mouth_open*.45)}" fill="none" stroke="#d28b80" stroke-width="1.4"/>')
    elif role != 'hero':
        parts.append('<path d="M-10 35 Q0 33 10 35" fill="none" stroke="#81554f" stroke-width="2.4" stroke-linecap="round"/>')
    else:
        parts.append('<path d="M-10 34 Q0 37 11 33" fill="none" stroke="#81554f" stroke-width="2.4" stroke-linecap="round"/>')
    if role!='hero':
        parts.extend([
            '<path d="M-59 -75 L-48 -102 Q0 -113 48 -102 L59 -75 Q0 -66 -59 -75Z" fill="#263a52" stroke="#202d3a" stroke-width="3"/>',
            '<path d="M-57 -77 Q0 -87 57 -77 L53 -68 Q0 -74 -53 -68Z" fill="#4c6580"/>',
            '<path d="M-59 -70 Q0 -81 59 -70 Q48 -62 0 -64 Q-48 -62 -59 -70Z" fill="#182b3b"/>',
            '<path d="M0 -99 L7 -96 L6 -88 L0 -84 L-6 -88 L-7 -96Z" fill="#e1bf73" stroke="#2c3a45" stroke-width="1.2"/>'])
    parts.append('</g>')
    if second:
        parts = [fragment.replace('url(#skin)','url(#skin2)') for fragment in parts]
    return ''.join(parts)


def torso(role='hero'):
    if role=='hero':
        return '''<path d="M-57 -469 Q-81 -460 -104 -451 Q-119 -443 -123 -424 L-111 -299 Q-110 -270 -91 -247 Q0 -234 91 -247 Q110 -268 111 -299 L123 -424 Q118 -444 104 -451 L57 -469Z" fill="url(#hoodie)" stroke="#245754" stroke-width="3"/>
        <path d="M-109 -425 Q-101 -349 -106 -303 L-92 -257 Q-53 -249 -38 -248 Q-75 -271 -77 -317 L-82 -434Z" fill="#174f56" opacity=".25"/>
        <path d="M-52 -467 Q0 -486 52 -467 L41 -423 Q15 -406 0 -406 Q-20 -408 -41 -423Z" fill="url(#hooddark)" stroke="#256f6d" stroke-width="2"/>
        <path d="M-47 -462 Q0 -473 47 -462 Q31 -438 0 -430 Q-31 -438 -47 -462Z" fill="#1c4a52"/>
        <path d="M-22 -434 Q-18 -410 -16 -382 M22 -434 Q18 -411 16 -382" fill="none" stroke="#d8e2d4" stroke-width="2" stroke-linecap="round"/>
        <path d="M-65 -301 Q-35 -312 0 -311 Q35 -312 65 -301 L72 -264 Q0 -257 -72 -264Z" fill="#207c79" opacity=".7"/>
        <path d="M-64 -302 Q0 -313 64 -302 M-48 -397 Q-73 -373 -76 -350 M53 -391 Q73 -367 77 -345 M-72 -272 Q0 -262 72 -272" fill="none" stroke="#8ed9c8" stroke-width="2" opacity=".5" stroke-linecap="round"/>'''
    return '''<path d="M-55 -470 Q-81 -461 -106 -453 Q-120 -447 -123 -423 L-110 -299 Q-108 -266 -94 -248 L94 -248 Q108 -266 110 -299 L123 -423 Q118 -445 105 -453 L55 -470Z" fill="url(#uniform)" stroke="#1d2e40" stroke-width="3"/>
    <path d="M-105 -424 Q-99 -340 -106 -300 L-94 -252 L-60 -251 Q-74 -319 -78 -435Z" fill="#142639" opacity=".27"/>
    <path d="M-50 -462 Q0 -476 50 -462 L30 -425 L0 -413 L-30 -425Z" fill="#d7e0df"/>
    <path d="M-8 -447 L8 -447 L11 -404 L0 -392 L-11 -404Z" fill="#1c3044"/>
    <path d="M-88 -411 Q-82 -428 -68 -430 L68 -430 Q82 -428 88 -411 L86 -289 L-86 -289Z" fill="#31475f" stroke="#24374b" stroke-width="2.2"/>
    <path d="M-73 -394 H-24 M26 -394 H73 M0 -425 V-292" fill="none" stroke="#8293a1" stroke-width="1.7" opacity=".6"/>
    <path d="M-103 -442 L-69 -449 M69 -449 L103 -442" fill="none" stroke="#aeb9bd" stroke-width="3"/>
    <path d="M48 -410 L58 -406 L57 -394 L48 -388 L39 -394 L38 -406Z" fill="#e1bf73" stroke="#24374b" stroke-width="1.5"/>
    <path d="M-90 -286 H90 V-264 H-90Z" fill="#1e3041"/><rect x="-10" y="-284" width="20" height="16" rx="2" fill="#d2b977"/>'''


def actor(x, ground, scale, *, role='hero', t=0, walk=0, phase=0,
          phone=0, has_phone=False, reach=0, emotion=0, look=0, tilt=0, lean=0, second=False):
    """A small articulated 2D rig, all moving elements redrawn each frame."""
    bob=abs(math.sin(phase))*4*walk + math.sin(t*2.1)*1.1*(1-walk)
    step=math.sin(phase)*30*walk
    lift_l=max(0,math.sin(phase))*16*walk
    lift_r=max(0,-math.sin(phase))*16*walk
    parts=[f'<g transform="translate({n(x)} {n(ground)}) scale({n(scale)})">',
           '<ellipse cx="0" cy="4" rx="77" ry="13" fill="#18252c" opacity=".18"/>',
           f'<g transform="translate(0 {n(-bob)})">']
    # Legs and shoes have independently moving knees and ankles.
    for side in (-1,1):
        stride=step if side==1 else -step
        lift=lift_r if side==1 else lift_l
        hip=(side*43,-258); ankle=(side*47+stride,-30-lift)
        knee=(mix(hip[0],ankle[0],.54)+(side*2),mix(hip[1],ankle[1],.53)-5*walk)
        parts.append(capsule(hip,knee,48,40,'url(#pants)'))
        parts.append(capsule(knee,ankle,41,32,'url(#pants)'))
        parts.append(f'<g transform="translate({n(ankle[0])} {n(ankle[1]+12)}) rotate({n(-stride*.12)})">'
                     '<path d="M-21 -9 Q-17 -14 -10 -12 L12 -9 Q19 -5 27 1 L30 8 Q30 13 25 14 L-23 14 Q-29 11 -27 5Z" fill="#26313d" stroke="#1d2934" stroke-width="2.2"/>'
                     '<path d="M-27 8 Q0 11 29 8 L29 13 Q2 17 -26 13Z" fill="#d8dfdb"/>'
                     '<path d="M4 -7 L12 -5 M-2 -5 L8 -3" stroke="#bcc8c6" stroke-width="1.3"/></g>')
    # The upper-body rig has a subtle independent weight shift and torso lean.
    roll=lean + math.sin(phase)*2.2*walk + math.sin(t*1.8)*.4*(1-walk)
    parts.append(f'<g transform="rotate({n(roll)} 0 -250)">')
    skin='skin2' if second else 'skin'
    # Far arm behind torso.
    sw=math.sin(phase)*24*walk
    lshoulder=(-103,-433); lelbow=(-121-sw*.30,-343); lhand=(-110-sw*.55,-277)
    rshoulder=(103,-433); relbow=(121+sw*.30,-343); rhand=(110+sw*.55,-277)
    if role=='hero':
        # First bring the handset up; later bring both wrists forward.
        relbow=pt((121,-351),(151,-431),phone)
        rhand=pt((91,-362),(54,-551),phone)
        if not has_phone:
            relbow=(121+sw*.30,-343); rhand=(110+sw*.55,-277)
        lelbow=pt(lelbow,(-40,-326),reach)
        lhand=pt(lhand,(94,-284),reach)
        relbow=pt(relbow,(110,-326),reach)
        rhand=pt(rhand,(110,-282),reach)
        sleeve='url(#hoodie)'
    else:
        lelbow=pt(lelbow,(-136,-332),reach)
        lhand=pt(lhand,(-142,-286),reach)
        relbow=pt(relbow,(124,-340),reach*.35)
        rhand=pt(rhand,(105,-288),reach*.35)
        sleeve='url(#uniform)'
    parts.extend([arm(lshoulder,lelbow,lhand,sleeve),hand(*lhand,angle=-5,skin=skin)])
    # Neck/torso and slight head acting.
    parts.append(f'<path d="M-25 -503 L-25 -455 Q0 -437 25 -455 L25 -503Z" fill="url(#{skin})" stroke="#71504c" stroke-width="2"/>')
    parts.append(torso(role))
    # Slight independent head motion with a held reaction.
    blink=0
    for center in (0.42,2.35,6.45,8.95):
        blink=max(blink, max(0,1-abs(t-center)/.095))
    parts.append(head(role,emotion,look,blink,tilt, t, second))
    # When reaching, the far forearm crosses the body instead of being hidden.
    if role=='hero' and reach>.01:
        parts.append(f'<g opacity="{n(reach)}">'+arm(lshoulder,lelbow,lhand,sleeve)+hand(*lhand,angle=-2,skin=skin)+'</g>')
    parts.extend([arm(rshoulder,relbow,rhand,sleeve),
                  hand(*rhand,angle=8,phone=has_phone,rotation=mix(-18,4,phone),ring=(1-phone)*clamp(1.15-t)*1.2,skin=skin)])
    parts.append('</g></g></g>')
    # Cuffs attach to the rigged hands after the same torso rotation.
    angle=math.radians(roll)
    def world(point):
        xx,yy=point[0],point[1]+250
        return (x+(xx*math.cos(angle)-yy*math.sin(angle))*scale,
                ground-bob*scale+(xx*math.sin(angle)+yy*math.cos(angle)-250)*scale)
    return ''.join(parts), world(lhand), world(rhand)


def svg_text(x,y,content,size=18,weight=700,fill='#f8fbf7',anchor='middle',extra=''):
    return f'<text x="{n(x)}" y="{n(y)}" text-anchor="{anchor}" font-family="DejaVu Sans" font-size="{size}" font-weight="{weight}" fill="{fill}" {extra}>{content}</text>'


def subtitle(text, y=811):
    # TikTok/Shorts safe area: left of interface controls, above the bottom HUD.
    shadow=svg_text(270,y+2,text,26,700,'#1b2836',extra='stroke="#1b2836" stroke-width="6" stroke-linejoin="round" paint-order="stroke"')
    return shadow + svg_text(270,y,text,26,700,'#f9faf6')


def incoming_card(t):
    pop=smooth(.1,.42,t); dismiss=smooth(2.5,2.94,t)
    y=45-(1-pop)*40-dismiss*115
    if y < -110: return ''
    ring_scale=1+.08*math.sin(t*9)*(1-smooth(1.1,1.5,t))
    return (f'<g transform="translate(54 {n(y)})">'
            '<rect x="4" y="6" width="432" height="107" rx="24" fill="#14232c" opacity=".16"/>'
            '<rect width="432" height="107" rx="24" fill="#f8fbf7" opacity=".96"/>'
            f'<g transform="translate(51 54) scale({n(ring_scale)})"><circle r="31" fill="#287d7a"/>'
            '<path d="M-12 -15 Q-16 -13 -15 -8 Q-11 7 5 14 Q11 16 14 10 L15 6 Q15 4 12 3 L6 0 Q4 -1 2 2 L0 4 Q-7 1 -9 -6 L-7 -8 Q-5 -10 -7 -13 L-10 -16Z" fill="#f5f9ee"/></g>'
            +svg_text(100,36,'ВХОДЯЩИЙ ЗВОНОК',13,700,'#728188','start')
            +svg_text(100,65,'ПОЛИЦИЯ',25,700,'#20313d','start')
            +svg_text(100,87,'на связи',13,400,'#728188','start')+'</g>')


def room_scene(t):
    # Subtle parallax and a portrait composition rather than a crop of the old clip.
    lift=smooth(.68,1.38,t)
    surprise=smooth(.28,.62,t)*(1-.45*smooth(1.95,2.7,t))
    tilt=mix(-3.0,4.5,surprise)+math.sin(t*2)*.6
    look=mix(2.8,-.7,lift)
    # A very slight dolly, not the movement itself.
    cam=1+0.014*smooth(0,3.1,t)
    a=[f'<g transform="translate({n(270*(1-cam))} {n(470*(1-cam))}) scale({n(cam)})">',
       '<rect width="540" height="960" fill="url(#room)"/>',
       '<path d="M0 0 H540 V585 H0Z" fill="#c5cfca"/>',
       '<path d="M0 30 L540 93 V160 L0 97Z" fill="#f0ede0" opacity=".18"/>',
       # Window and balcony/city layers.
       '<rect x="-55" y="130" width="285" height="436" rx="7" fill="#34505b"/>',
       '<rect x="-43" y="142" width="260" height="411" fill="url(#sky)"/>',
       '<path d="M-43 405 L5 357 L62 383 L110 326 L165 357 L217 315 V553 H-43Z" fill="#5d7880" opacity=".55"/>',
       '<path d="M-43 466 Q28 440 100 466 Q163 435 217 449 V553 H-43Z" fill="#668a86" opacity=".65"/>',
       '<path d="M81 142 V553 M-43 342 H217" stroke="#34505b" stroke-width="9"/>',
       '<path d="M-42 150 H217 M-42 551 H217" stroke="#f5f0df" stroke-width="7" opacity=".65"/>',
       # Curtains appear layered and sway very slightly.
       f'<path d="M-5 120 Q{n(17+math.sin(t)*3)} 273 8 514 L-35 558 L-55 558 V120Z" fill="#eef2e8" opacity=".66"/>',
       '<path d="M228 130 Q207 279 229 524 L245 558 H273 V130Z" fill="#e9eee4" opacity=".49"/>',
       '<path d="M0 570 H540 V960 H0Z" fill="#6d8285"/>',
       '<path d="M0 582 L540 545 V662 L0 705Z" fill="#384e59" opacity=".16"/>',
       # Contemporary furniture, with layered soft shading.
       '<path d="M-20 631 Q-19 601 12 592 L360 585 Q411 587 424 626 L437 808 H-20Z" fill="#788d8a" stroke="#465f61" stroke-width="3"/>',
       '<path d="M-6 652 Q-5 625 24 622 L200 618 L206 752 H-6 M211 618 L355 615 Q390 617 394 646 L404 752 H211Z" fill="#a8b9ab" stroke="#708a83" stroke-width="3"/>',
       '<path d="M-16 760 Q175 738 410 756 L426 840 H-16Z" fill="#819b93" stroke="#526f6a" stroke-width="3"/>',
       # Lamp.
       '<path d="M471 295 V691" stroke="#475b5e" stroke-width="6"/><path d="M432 299 Q471 263 510 299 L500 332 H442Z" fill="#ece4cd" stroke="#53645f" stroke-width="2"/>',
       '<ellipse cx="471" cy="333" rx="65" ry="54" fill="url(#warmglow)"/>',
       '<rect width="540" height="960" fill="url(#roomshade)"/>']
    actor_svg,_,_=actor(237,1544,2.15,role='hero',t=t,phone=lift,has_phone=True,
                        emotion=surprise,look=look,tilt=tilt,lean=-1.5*surprise)
    a += [actor_svg,'</g>',incoming_card(t)]
    if t>1.18:
        a.append(subtitle('ПОЛИЦИЯ?..',813))
    return ''.join(a)


def shrub(x,y,s=1):
    return (f'<g transform="translate({x} {y}) scale({s})">'
            '<path d="M-80 12 Q-95 -9 -75 -22 Q-71 -43 -50 -41 Q-40 -61 -18 -53 Q0 -70 20 -52 Q44 -61 54 -38 Q75 -41 78 -19 Q98 -5 79 12Z" fill="#547d70" stroke="#3e665c" stroke-width="2"/>'
            '<path d="M-64 -19 Q-41 -32 -30 -20 M-10 -36 Q5 -46 18 -35 M35 -23 Q49 -32 63 -20" fill="none" stroke="#89ad94" stroke-width="2" opacity=".6"/></g>')


def house_wide(t):
    # The same architectural details recur in the porch shot.
    return '''<g>
      <path d="M0 609 Q65 576 135 595 Q205 567 277 589 Q372 566 453 594 Q505 582 540 590 V744 H0Z" fill="#597b73"/>
      <path d="M391 233 L391 190 L425 190 L425 316 L391 298Z" fill="#4c5c66" stroke="#263a48" stroke-width="3"/>
      <path d="M24 326 L241 194 L473 326 L459 344 H40Z" fill="url(#roof)" stroke="#243542" stroke-width="5"/>
      <path d="M39 333 L241 214 L459 335 V682 H39Z" fill="url(#wall)" stroke="#54636a" stroke-width="3"/>
      <path d="M38 333 L241 211 L462 334" fill="none" stroke="#dde4db" stroke-width="6"/>
      <path d="M45 364 H453 M45 431 H453 M45 499 H453 M45 567 H453 M45 635 H453" stroke="#9faea7" stroke-width="1.4" opacity=".35"/>
      <rect x="79" y="448" width="114" height="230" rx="3" fill="#3d5d62" stroke="#314950" stroke-width="5"/>
      <rect x="90" y="459" width="92" height="207" fill="#547c7d"/>
      <path d="M100 470 H172 V547 H100Z" fill="url(#glass)" stroke="#375963" stroke-width="3"/>
      <path d="M106 478 L136 478 L106 519Z" fill="#eff7e7" opacity=".3"/>
      <circle cx="165" cy="589" r="4" fill="#ead297"/>
      <path d="M65 678 H207 L224 691 H52Z" fill="#e5e3d4" stroke="#7d918d" stroke-width="2"/>
      <path d="M65 691 H213 L246 733 H32Z" fill="#b1b7a9"/>
      <rect x="265" y="410" width="142" height="129" fill="#e8dfcd" stroke="#526668" stroke-width="5"/>
      <rect x="273" y="418" width="126" height="113" fill="url(#glass)"/>
      <path d="M336 418 V531 M273 475 H399" stroke="#536c6d" stroke-width="5"/>
      <path d="M279 423 H315 L279 458Z" fill="#f2f8e9" opacity=".35"/>
      <path d="M257 539 H415 L410 548 H262Z" fill="#8b9c95"/>
      <path d="M227 294 Q241 277 255 294 V336 H227Z" fill="#6d8787" stroke="#dae1d7" stroke-width="4"/>
      <path d="M241 292 V335 M228 315 H255" stroke="#dae1d7" stroke-width="3"/>
      </g>'''+shrub(37,674,.8)+shrub(464,678,.95)


def wheel(cx,cy,angle,r=31):
    return (f'<g transform="translate({n(cx)} {n(cy)}) rotate({n(angle)})">'
            f'<circle r="{r}" fill="#25333f"/><circle r="{r*.77}" fill="#47535c"/>'
            f'<circle r="{r*.55}" fill="#b8c7c4"/><circle r="{r*.19}" fill="#42565f"/>'
            +''.join(f'<path d="M0 {-r*.48} L{-r*.09} {-r*.21} L{r*.09} {-r*.21}Z" fill="#53666d" transform="rotate({i*72})"/>' for i in range(5))+'</g>')


def police_car(x,y,s,t,rotation=0,opacity=1):
    flash=math.sin(t*math.pi*4.4)
    red=.35+.65*max(0,flash); blue=.35+.65*max(0,-flash)
    return (f'<g transform="translate({n(x)} {n(y)}) scale({n(s)})" opacity="{opacity}">'
        '<ellipse cx="205" cy="9" rx="205" ry="18" fill="#1e2d38" opacity=".25"/>'
        # Roof and windshield, body and trim use separate layers.
        '<path d="M102 -97 L142 -145 Q150 -154 166 -155 H266 Q285 -154 301 -138 L337 -96Z" fill="#233d50" stroke="#253645" stroke-width="3"/>'
        '<path d="M117 -100 L148 -137 Q154 -145 165 -145 H199 V-100Z" fill="url(#glass)"/>'
        '<path d="M208 -145 H263 Q278 -144 288 -134 L316 -100 H208Z" fill="url(#glass)"/>'
        '<path d="M132 -104 L152 -130 M222 -140 H257" stroke="#d8f1ed" stroke-width="3" opacity=".6"/>'
        '<path d="M15 -82 Q34 -96 102 -101 H338 Q376 -98 404 -84 Q417 -78 418 -65 L419 -34 Q419 -22 408 -21 H12 Q5 -22 6 -34 L6 -58 Q6 -73 15 -82Z" fill="url(#car)" stroke="#293c49" stroke-width="3"/>'
        '<path d="M8 -68 H418 V-50 H8Z" fill="#4b80a0"/><path d="M8 -49 H418 V-43 H8Z" fill="#dce9e3" opacity=".45"/>'
        '<path d="M205 -98 V-24 M333 -97 L337 -24" stroke="#667d83" stroke-width="2"/>'
        '<path d="M219 -91 H235 M345 -91 H359" stroke="#526c76" stroke-width="3" stroke-linecap="round"/>'
        '<path d="M11 -80 H27 V-68 H7Z" fill="#ffe7ac" stroke="#c9a76e" stroke-width="1.4"/>'
        '<path d="M405 -77 H417 V-61 H405Z" fill="#d77b74"/>'
        '<path d="M5 -35 H23 V-24 H5 M402 -35 H421 V-24 H402" fill="#364953"/>'
        '<path d="M258 -78 L269 -74 L268 -60 L258 -53 L248 -60 L247 -74Z" fill="#d8ba77" stroke="#38505d" stroke-width="1.5"/>'
        +svg_text(277,-32,'ПОЛИЦИЯ',9,700,'#3a5d70','start')+
        wheel(94,-27,rotation,31)+wheel(337,-27,rotation,31)+
        '<path d="M189 -161 H245 V-153 H189Z" fill="#283a48"/>'
        f'<ellipse cx="203" cy="-167" rx="54" ry="43" fill="url(#redglow)" opacity="{n(red)}"/>'
        f'<ellipse cx="233" cy="-167" rx="54" ry="43" fill="url(#blueglow)" opacity="{n(blue)}"/>'
        f'<rect x="190" y="-171" width="25" height="11" rx="4" fill="#ff6c75" opacity="{n(red)}" stroke="#2b3d4a" stroke-width="2"/>'
        f'<rect x="220" y="-171" width="25" height="11" rx="4" fill="#58c9fa" opacity="{n(blue)}" stroke="#2b3d4a" stroke-width="2"/>'
        '</g>')


def street_scene(t):
    local=t-3.1
    travel=smooth(.05,1.82,local)
    x=mix(600,59,travel)
    bounce=1.5*math.sin(local*14)*(1-travel)
    cam=1+.015*smooth(0,2.7,local)
    sky_moves=math.sin(local*.45)*6
    red=max(0,math.sin(t*math.pi*4.4)); blue=max(0,-math.sin(t*math.pi*4.4))
    a=[f'<g transform="translate({n(270*(1-cam))} {n(500*(1-cam))}) scale({n(cam)})">',
       '<rect width="540" height="960" fill="url(#sky)"/>',
       f'<path d="M{n(-80+sky_moves)} 182 Q-13 155 42 175 Q77 153 134 173 L184 184 Q151 195 104 192 Q45 208 -13 195Z" fill="#e4e9de" opacity=".24"/>',
       '<path d="M-30 519 L10 426 L42 519 M470 512 L505 398 L552 514" fill="#3d6261" opacity=".55"/>',
       house_wide(t),
       # Light reflecting off the facade, subdued enough to preserve readability.
       f'<ellipse cx="342" cy="565" rx="185" ry="150" fill="url(#redglow)" opacity="{n(red*.25*travel)}"/>',
       f'<ellipse cx="350" cy="555" rx="185" ry="150" fill="url(#blueglow)" opacity="{n(blue*.25*travel)}"/>',
       '<path d="M0 718 H540 V960 H0Z" fill="url(#road)"/>',
       '<path d="M0 715 H540 V738 H0Z" fill="#c6c8b9"/>',
       '<path d="M0 844 Q210 839 540 846" stroke="#90a09f" stroke-width="1.5" opacity=".4"/>',
       '<path d="M16 912 H170 M266 912 H422" stroke="#d8d3bd" stroke-width="5" stroke-linecap="round" opacity=".8"/>']
    # The car enters from the right, moving left. Its wheels actually turn.
    a.append(police_car(x,790+bounce,1.0,t,(600-x)*.35))
    a.append('</g>')
    a.append(subtitle('ПОЛИЦИЯ У ДОМА',829))
    return ''.join(a)


def porch_background(local,t):
    op=smooth(.05,.55,local)
    width=172*(1-.72*op)
    red=max(0,math.sin(t*math.pi*4.4)); blue=max(0,-math.sin(t*math.pi*4.4))
    return ('''<rect width="540" height="960" fill="#b9c9c3"/>
      <path d="M0 0 H540 V739 H0Z" fill="url(#wall)"/>
      <path d="M0 95 H540 M0 195 H540 M0 295 H540 M0 395 H540 M0 495 H540 M0 595 H540" stroke="#a5b2a9" stroke-width="2" opacity=".24"/>
      <rect x="40" y="184" width="203" height="540" rx="4" fill="#354b51" stroke="#526668" stroke-width="7"/>
      <rect x="54" y="198" width="176" height="510" fill="#263a44"/>
      <rect x="301" y="255" width="211" height="200" fill="#eee7d7" stroke="#526668" stroke-width="7"/>
      <rect x="312" y="266" width="189" height="178" fill="url(#glass)"/>
      <path d="M406 266 V444 M312 354 H501" stroke="#536c6d" stroke-width="7"/>
      <path d="M323 277 H375 L323 331Z" fill="#eef8ee" opacity=".28"/>
      <path d="M289 456 H523 L515 468 H296Z" fill="#94a59d"/>
      <circle cx="277" cy="218" r="54" fill="url(#warmglow)"/>
      <path d="M268 200 H285 L289 226 H264Z" fill="#eacb85" stroke="#687b73" stroke-width="3"/>
      <rect x="0" y="725" width="540" height="235" fill="#bcc4b9"/>
      <path d="M0 780 H540 M0 889 H540 M155 725 L102 960 M420 725 L468 960" fill="none" stroke="#869a93" stroke-width="2" opacity=".55"/>'''
      +shrub(535,708,.85)+
      f'<ellipse cx="445" cy="610" rx="200" ry="200" fill="url(#redglow)" opacity="{n(red*.17)}"/>'
      f'<ellipse cx="468" cy="610" rx="200" ry="200" fill="url(#blueglow)" opacity="{n(blue*.17)}"/>'
      # Hinged door, glass insert follows the door's own opening transform.
      f'<path d="M54 198 L{n(54+width)} {n(198+12*op)} L{n(54+width)} {n(708-10*op)} L54 708Z" fill="#547c7d" stroke="#334e55" stroke-width="4"/>'
      f'<path d="M{n(54+width*.13)} 228 L{n(54+width*.85)} {n(230+8*op)} L{n(54+width*.85)} {n(378+8*op)} L{n(54+width*.13)} 375Z" fill="url(#glass)" stroke="#3a5c64" stroke-width="3"/>'
      f'<circle cx="{n(54+width*.83)}" cy="500" r="4.5" fill="#ebd198"/>'
      '<path d="M30 720 H253 V733 H30Z" fill="#e8e8d8" stroke="#788c86" stroke-width="2"/>')


def cuffs(a,b,local):
    show=smooth(2.35,2.65,local)
    if show<=0: return ''
    x1,y1=a; x2,y2=b
    open_angle=(1-show)*35
    return (f'<g opacity="{n(show)}" fill="none" stroke-linecap="round">'
            f'<path d="M{n(x1)} {n(y1)} Q{n((x1+x2)/2)} {n((y1+y2)/2+7)} {n(x2)} {n(y2)}" stroke="#344553" stroke-width="5"/>'
            f'<path d="M{n(x1)} {n(y1)} Q{n((x1+x2)/2)} {n((y1+y2)/2+7)} {n(x2)} {n(y2)}" stroke="#e2e8df" stroke-width="2"/>'
            +''.join(f'<ellipse cx="{n(x)}" cy="{n(y)}" rx="9" ry="7" transform="rotate({n(open_angle)} {n(x)} {n(y)})" stroke="#273f4c" stroke-width="6"/><ellipse cx="{n(x)}" cy="{n(y)}" rx="9" ry="7" transform="rotate({n(open_angle)} {n(x)} {n(y)})" stroke="#ecf0e9" stroke-width="3"/>' for x,y in (a,b))+'</g>')


def porch_scene(t):
    local=t-5.8
    hero_x=mix(88,153,smooth(.08,.93,local))
    police_x=mix(628,366,smooth(.14,1.92,local))
    police2_x=mix(690,526,smooth(.30,2.15,local))
    hero_walk=1-smooth(.70,1.03,local)
    cop_walk=1-smooth(1.60,1.97,local)
    reach=smooth(1.62,2.50,local)
    hero_reaction=smooth(.55,1.05,local)*(1-.25*smooth(3.0,4.2,local))
    cam=1+.025*smooth(.2,4.2,local)
    a=[f'<g transform="translate({n(270*(1-cam))} {n(570*(1-cam))}) scale({n(cam)})">',
       '<rect width="540" height="960" fill="#bcc4b9"/><g transform="scale(1 .92)">',porch_background(local,t),'</g>']
    # Car is parked behind the actors, higher in the shot for depth.
    a.append(police_car(387,690,.78,t,0))
    back,_,_=actor(police2_x,746,.72,role='police',t=t,walk=cop_walk,phase=local*9-.9,look=-2,second=True)
    a.append(back)
    hero,left,right=actor(hero_x,760,.81,role='hero',t=t,walk=hero_walk,phase=local*11,
                          reach=reach,emotion=hero_reaction,look=2.0,tilt=mix(-2,5,hero_reaction),lean=-1.3*hero_reaction)
    cop,_,_=actor(police_x,760,.81,role='police',t=t,walk=cop_walk,phase=local*9.4,
                  reach=reach,emotion=.04,look=-2.4,tilt=-2,lean=1.1*reach)
    a.extend([hero,cop,cuffs(left,right,local),'</g>'])
    if local>2.22:
        a.append(subtitle('ГЕРОЯ ЗАДЕРЖАЛИ',829))
    return ''.join(a)


def frame_svg(t):
    if t<3.1: body=room_scene(t)
    elif t<5.8: body=street_scene(t)
    else: body=porch_scene(t)
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">'
            +DEFS+body+'<rect width="540" height="960" fill="url(#vig)" pointer-events="none"/></svg>')


def frame_png(t,w=OUTPUT_W,h=OUTPUT_H):
    return resvg_py.svg_to_bytes(svg_string=frame_svg(t),width=w,height=h,
                                 skip_system_fonts=True,font_files=FONT_FILES)


def decode_sample(path,sr=44100):
    ff=imageio_ffmpeg.get_ffmpeg_exe()
    p=subprocess.run([ff,'-v','error','-i',str(path),'-f','f32le','-ac','2','-ar',str(sr),'-'],
                     check=True,stdout=subprocess.PIPE)
    return np.frombuffer(p.stdout,dtype='<f4').reshape(-1,2).astype(np.float64)


def soundtrack():
    sr=44100; length=sr*DURATION
    tt=np.arange(length,dtype=np.float64)/sr
    track=np.zeros((length,2),dtype=np.float64)
    rng=np.random.default_rng(47)
    def add(start,data,vol=1,pan=0):
        start=int(round(start*sr)); size=min(len(data),length-start)
        if start<0 or size<=0: return
        if data.ndim==1:
            track[start:start+size,0]+=data[:size]*vol*(1-.35*pan)
            track[start:start+size,1]+=data[:size]*vol*(1+.35*pan)
        else:
            track[start:start+size,0]+=data[:size,0]*vol*(1-.35*pan)
            track[start:start+size,1]+=data[:size,1]*vol*(1+.35*pan)
    # Low, modern cinematic bed: no cartoonish chiptune.
    chords=[(110,164.81,220),(98,146.83,196),(103.83,155.56,207.65),(87.31,130.81,174.61)]
    for j,start in enumerate(np.arange(0,DURATION,2.6)):
        duration=min(3.2,DURATION-start)
        u=np.arange(int(sr*duration))/sr
        fade=np.minimum(1,u/.35)*np.minimum(1,(duration-u)/.7)
        tone=sum(np.sin(2*np.pi*f*u+0.4*i)*(.5 if i==0 else .22) for i,f in enumerate(chords[j%len(chords)]))
        tone+=.15*np.sin(2*np.pi*chords[j%len(chords)][0]*2.01*u)
        add(start,tone*fade,.055)
    for j,start in enumerate(np.arange(.18,DURATION,.54)):
        u=np.arange(int(sr*.18))/sr
        kick=np.sin(2*np.pi*(61*u-35*u*u))*np.exp(-u*23)
        add(start,kick,.048, -.25 if j%2 else .25)
    # Discrete phone ring and pickup click.
    for start in (.22,.82):
        u=np.arange(int(sr*.28))/sr
        env=np.minimum(1,u/.025)*np.minimum(1,(.28-u)/.04)
        ring=(np.sin(2*np.pi*480*u)+np.sin(2*np.pi*620*u))*.5*env
        add(start,ring,.10,.3)
    u=np.arange(int(sr*.055))/sr
    add(1.38,(np.sin(2*np.pi*1600*u)+.3*rng.normal(size=len(u)))*np.exp(-u*68),.035,.3)
    # Approaching motor + rising/falling siren, both fade with the shot.
    duration=3.0; u=np.arange(int(sr*duration))/sr
    env=np.minimum(1,u/.55)*np.minimum(1,(duration-u)/.55)
    engine=(np.sin(2*np.pi*(70*u+10*u*u))+.2*rng.normal(size=len(u)))*env
    add(3.0,engine,.035,.32)
    hz=620+190*np.sin(2*np.pi*.85*u)
    phase=2*np.pi*np.cumsum(hz)/sr
    siren=(np.sin(phase)+.2*np.sin(phase*2))*env
    add(3.15,siren,.075,.26)
    # Real-world CC0 foley samples (Kenney): door, footsteps, metal closure.
    door=decode_sample(SOUNDS/'doorOpen_1.ogg',sr)
    step0=decode_sample(SOUNDS/'footstep_concrete_000.ogg',sr)
    step1=decode_sample(SOUNDS/'footstep_concrete_003.ogg',sr)
    metal=decode_sample(SOUNDS/'metalClick.ogg',sr)
    latch=decode_sample(SOUNDS/'metalLatch.ogg',sr)
    add(5.88,door,.10,-.2)
    for j,start in enumerate((6.04,6.27,6.52,6.76,7.0,7.23,7.46)):
        add(start,step0 if j%2==0 else step1,.18,(-.45 if j%2 else .4))
    add(8.22,metal,.16,-.10)
    add(8.43,latch,.12,-.10)
    fade=np.minimum(1,tt/.08)*np.minimum(1,(DURATION-tt)/.1)
    track*=fade[:,None]
    peak=np.max(np.abs(track))
    if peak>0: track*=.82/peak
    return (track*32767).astype('<i2'),sr


def write_wav(path):
    samples,sr=soundtrack()
    with wave.open(str(path),'wb') as f:
        f.setnchannels(2); f.setsampwidth(2); f.setframerate(sr); f.writeframes(samples.tobytes())


def render_video(output=OUT,width=OUTPUT_W,height=OUTPUT_H):
    output.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='nurmadog-modern-') as temp:
        wav=Path(temp)/'sound.wav'; write_wav(wav)
        cmd=[imageio_ffmpeg.get_ffmpeg_exe(),'-hide_banner','-loglevel','error','-y',
             '-f','image2pipe','-vcodec','png','-framerate',str(FPS),'-i','-',
             '-i',str(wav),'-t',str(DURATION),'-c:v','libx264','-preset','veryfast',
             '-crf','19','-pix_fmt','yuv420p','-c:a','aac','-b:a','160k','-movflags','+faststart',str(output)]
        proc=subprocess.Popen(cmd,stdin=subprocess.PIPE)
        try:
            for i in range(FPS*DURATION):
                proc.stdin.write(frame_png(i/FPS,width,height))
                if i%30==0: print(f'frame {i}/{FPS*DURATION}',flush=True)
        finally:
            proc.stdin.close()
        if proc.wait()!=0: raise RuntimeError('ffmpeg failed')
    print(f'Wrote {output} ({output.stat().st_size/1_000_000:.1f} MB)',flush=True)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--samples',action='store_true',help='Internal animation QA frames')
    parser.add_argument('--width',type=int,default=OUTPUT_W)
    parser.add_argument('--height',type=int,default=OUTPUT_H)
    parser.add_argument('--output',type=Path,default=OUT)
    args=parser.parse_args()
    if args.samples:
        folder=ROOT/'animation'/'previews'; folder.mkdir(parents=True,exist_ok=True)
        for t in (.3,.8,1.4,2.3,3.7,4.9,6.3,7.3,8.5,9.5):
            path=folder/f'modern_{t:.2f}.png'; path.write_bytes(frame_png(t,540,960)); print(path)
    else:
        render_video(args.output,args.width,args.height)

if __name__=='__main__': main()
