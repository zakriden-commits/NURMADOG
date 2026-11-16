#!/usr/bin/env python3
"""Вмешаться, episode 1 — a hand-keyframed, vertical 2D animated short.

No photographs or still images are animated. Every visible character and prop
is drawn as vector geometry and posed independently on each frame. Spoken
clips are separate, user-selected voices; foley is mixed to picture.
"""
from __future__ import annotations
import argparse
import math
import subprocess
import sys
import tempfile
import wave
from pathlib import Path

import imageio_ffmpeg
import numpy as np
import resvg_py

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT/'animation'))
import modern_shorts as art

W,H=540,960
FPS,DURATION=24,60
RENDER_W,RENDER_H=720,1280
OUTPUT_W,OUTPUT_H=1080,1920
OUT=ROOT/'videos'/'vmeshat_sya_episode_01.mp4'
FONT_FILES=art.FONT_FILES
VOICE_DIR=HERE/'voices'
SOUND_DIR=HERE/'sounds'
FOLEY_DIR=ROOT/'animation'/'sounds'

n=art.n
smooth=art.smooth
mix=art.mix
pt=art.pt
clamp=art.clamp

# Timecodes are deliberately explicit so animation, dialogue, foley and captions
# stay synchronized if the episode is regenerated.
VOICES=[
    ('hero_01_night.wav',.45,'hero',False),
    ('man_01_shouting.wav',6.10,'man',True),
    ('woman_01_help.wav',9.70,'woman',True),
    ('hero_02_witness.wav',13.00,'hero',False),
    ('hero_03_memory.wav',20.25,'hero',False),
    ('hero_04_decision.wav',29.60,'hero',False),
    ('man_02_door.wav',39.50,'man',False),
    ('hero_05_question.wav',41.15,'hero',False),
    ('man_03_warning.wav',44.25,'man',False),
    ('hero_06_angry.wav',48.75,'hero',False),
]

EXTRA_DEFS='''<defs>
<linearGradient id="nightSky" x1="0" y1="0" x2="0" y2="1"><stop stop-color="#0b1728"/><stop offset="1" stop-color="#344b59"/></linearGradient>
<linearGradient id="apartment" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#54666a"/><stop offset="1" stop-color="#344852"/></linearGradient>
<linearGradient id="court" x1="0" y1="0" x2="0" y2="1"><stop stop-color="#4d6263"/><stop offset="1" stop-color="#273b42"/></linearGradient>
<linearGradient id="warmRoom" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#e5c89e"/><stop offset="1" stop-color="#aa8c73"/></linearGradient>
<linearGradient id="hall" x1="0" y1="0" x2="0" y2="1"><stop stop-color="#a8aba0"/><stop offset="1" stop-color="#697e7d"/></linearGradient>
<linearGradient id="wood" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#8a6a58"/><stop offset="1" stop-color="#4a3b3b"/></linearGradient>
<linearGradient id="goldHair" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#f0cf73"/><stop offset=".6" stop-color="#d5a848"/><stop offset="1" stop-color="#b98436"/></linearGradient>
<radialGradient id="lampGlow"><stop stop-color="#ffdb9b" stop-opacity=".7"/><stop offset="1" stop-color="#ffdb9b" stop-opacity="0"/></radialGradient>
<radialGradient id="memoryGlow"><stop stop-color="#ffe9c6" stop-opacity=".25"/><stop offset="1" stop-color="#533e36" stop-opacity=".35"/></radialGradient>
</defs>'''


def load_wav(path):
    with wave.open(str(path),'rb') as f:
        if f.getsampwidth()!=2: raise ValueError(f'expected 16-bit PCM: {path}')
        samples=np.frombuffer(f.readframes(f.getnframes()),dtype='<i2').astype(np.float32)/32768
        if f.getnchannels()>1: samples=samples.reshape(-1,f.getnchannels()).mean(axis=1)
        return samples, f.getframerate()


_VOICE_CACHE={}
def voice_data(name):
    if name not in _VOICE_CACHE:
        data,sr=load_wav(VOICE_DIR/name)
        _VOICE_CACHE[name]=(data,sr)
    return _VOICE_CACHE[name]


def speech_amp(role,t):
    """Approximate lip motion from the real voice waveform rather than a loop."""
    value=0.
    for filename,start,speaker,_ in VOICES:
        if speaker!=role: continue
        data,sr=voice_data(filename)
        pos=int((t-start)*sr)
        if 0<=pos<len(data):
            window=data[max(0,pos-500):min(len(data),pos+500)]
            if len(window): value=max(value,min(1,float(np.sqrt(np.mean(window*window)))*7))
    return value


def text(x,y,content,size=20,weight=700,fill='#f5f7f1',anchor='middle',extra=''):
    return art.svg_text(x,y,content,size,weight,fill,anchor,extra)


def face(role='hero',emotion=0,look=0,t=0,talk=0,tilt=0):
    ishero=role in ('hero','child')
    woman=role in ('woman','mom')
    beard=role=='hero'
    angry=role in ('man','dad')
    hair='#dcae52' if ishero else ('#473d3f' if woman else '#30343c')
    blink=max(0,1-abs((t+(.7 if role=='man' else 0))%4.2-.1)/.09)
    eye=max(.09,(1+.18*emotion)*(1-blink*.95))
    a=[f'<g transform="translate(0 -540) rotate({n(tilt)})">',
       '<path d="M-48 -18 C-62 -31 -66 -9 -54 8 Q-51 12 -46 10 M48 -18 C62 -31 66 -9 54 8 Q51 12 46 10" fill="url(#skin)" stroke="#72544e" stroke-width="2.2"/>',
       '<path d="M-50 -55 C-58 -30 -56 2 -48 26 C-42 46 -25 64 -7 70 C0 72 7 71 13 68 C31 60 44 43 49 22 C56 -6 56 -36 47 -58 Q32 -83 0 -84 Q-34 -85 -50 -55Z" fill="url(#skin)" stroke="#71504c" stroke-width="2.4"/>',
       '<path d="M-47 -20 C-50 8 -43 38 -25 55 Q-39 45 -40 20Z" fill="#a9655b" opacity=".16"/>']
    if woman:
        a.append('<path d="M-53 -38 Q-66 -88 -29 -99 Q1 -119 35 -95 Q60 -80 54 -36 L60 20 Q47 31 43 25 L43 -54 Q19 -70 -4 -68 Q-27 -62 -43 -59 L-44 27 Q-58 30 -60 17Z" fill="#574247" stroke="#3d363a" stroke-width="2"/>')
    else:
        fill='url(#goldHair)' if ishero else hair
        border='#9e763b' if ishero else '#26313a'
        highlight='#f7d989' if ishero else '#65706e'
        a.append(f'<path d="M-52 -33 C-61 -44 -63 -60 -57 -76 C-53 -89 -44 -97 -30 -99 C-24 -111 -10 -114 0 -108 C11 -115 24 -111 29 -102 C45 -102 55 -93 57 -80 Q62 -64 51 -36 L45 -58 Q37 -55 30 -64 Q19 -58 10 -67 Q-2 -60 -12 -69 Q-27 -60 -40 -61 L-45 -36Z" fill="{fill}" stroke="{border}" stroke-width="2.5"/>')
        a.append(f'<path d="M-42 -83 Q-22 -99 -3 -94 M8 -100 Q27 -103 42 -89" fill="none" stroke="{highlight}" stroke-width="2" opacity=".8"/>')
    # Anger pulls the brows inward; fear lifts the middle. Pupils remain separate.
    frown = emotion if (angry or (role=='hero' and emotion>.7)) else -emotion*.55
    outer, inner = -26-4*frown, -24+5*frown
    a.append(f'<path d="M-34 {n(outer)} Q-23 {n((outer+inner)/2-2)} -11 {n(inner)} M10 {n(inner)} Q22 {n((outer+inner)/2-2)} 34 {n(outer)}" fill="none" stroke="#413a38" stroke-width="3.5" stroke-linecap="round"/>')
    if eye<.3:
        a.append('<path d="M-34 -6 Q-22 -2 -11 -7 M11 -7 Q22 -2 34 -6" fill="none" stroke="#3a3938" stroke-width="2.5"/>')
    else:
        a.append(f'<g transform="translate(0 -6) scale(1 {n(eye)}) translate(0 6)"><path d="M-34 -6 Q-23 -15 -11 -7 Q-22 1 -34 -6 M11 -7 Q22 -15 34 -6 Q23 1 11 -7" fill="#faf4e9" stroke="#62534d" stroke-width="1.5"/><circle cx="{n(-21+look)}" cy="-6" r="4.6" fill="#3d5653"/><circle cx="{n(22+look)}" cy="-6" r="4.6" fill="#3d5653"/><circle cx="{n(-20+look)}" cy="-7.5" r="1.2" fill="#fff"/><circle cx="{n(23+look)}" cy="-7.5" r="1.2" fill="#fff"/></g>')
    a.append('<path d="M1 -3 Q7 10 3 16 Q0 18 -5 15" fill="none" stroke="#a86f5f" stroke-width="2" stroke-linecap="round"/>')
    if beard:
        # The selected full-body reference has gold hair and a full golden beard.
        a.append('<path d="M-49 9 Q-47 40 -29 58 Q0 83 29 58 Q47 39 49 9 L41 7 Q39 25 27 30 Q20 20 9 23 Q0 20 -9 23 Q-20 20 -27 30 Q-39 25 -41 7Z" fill="url(#goldHair)" stroke="#a77938" stroke-width="2.2"/>')
        a.append('<path d="M-23 26 Q-13 15 0 23 Q13 15 23 26 Q17 31 10 29 L0 27 L-10 29 Q-17 31 -23 26Z" fill="#ddb054" stroke="#a77938" stroke-width="1.3"/>')
    if talk>.08:
        a.append(f'<ellipse cx="0" cy="37" rx="8" ry="{n(1.3+4.7*talk)}" fill="#71454a"/><path d="M-4 39 Q0 41 4 39" fill="none" stroke="#d58c7f" stroke-width="1.3"/>')
    elif emotion>.35:
        a.append('<path d="M-10 37 Q0 32 10 37" fill="none" stroke="#7b514a" stroke-width="2.4" stroke-linecap="round"/>')
    else:
        a.append('<path d="M-10 35 Q0 37 11 34" fill="none" stroke="#80534d" stroke-width="2.4" stroke-linecap="round"/>')
    a.append('</g>')
    return ''.join(a)


def shirt(role):
    if role in ('hero','child'): return art.torso('hero')
    fill={'man':'#493f45','dad':'#755358','woman':'#ad7877','mom':'#b68380','uncle':'#777566'}.get(role,'#5c6772')
    return (f'<path d="M-57 -469 Q-81 -460 -104 -451 Q-119 -443 -123 -424 L-111 -299 Q-110 -270 -91 -247 Q0 -234 91 -247 Q110 -268 111 -299 L123 -424 Q118 -444 104 -451 L57 -469Z" fill="{fill}" stroke="#303b43" stroke-width="3"/>'
            '<path d="M-47 -460 Q0 -447 47 -460 Q30 -434 0 -431 Q-30 -434 -47 -460Z" fill="#2b353d" opacity=".32"/>'
            '<path d="M-89 -374 Q-82 -319 -91 -272 M86 -374 Q78 -319 88 -271 M-67 -261 Q0 -254 67 -261" fill="none" stroke="#f0ded1" stroke-width="2" opacity=".18"/>')


def tattoo(a,b):
    dx=b[0]-a[0]; dy=b[1]-a[1]
    x=(a[0]+b[0])/2; y=(a[1]+b[1])/2
    ang=math.degrees(math.atan2(dy,dx))
    return (f'<g transform="translate({n(x)} {n(y)}) rotate({n(ang)})" fill="none" stroke="#33434a" stroke-width="2.5" opacity=".85">'
            '<path d="M-24 -8 L-16 4 L-8 -6 L0 7 L8 -6 L16 5 L24 -7 M-18 10 H18"/><circle r="4"/></g>')


def relaxed_hand(x,y,angle=0):
    """Open hand for conversation and resting poses (the closed hand is a fist)."""
    return (f'<g transform="translate({n(x)} {n(y)}) rotate({n(angle)})">'
            '<path d="M-12 -11 Q-16 -6 -14 2 L-11 14 Q-9 19 -7 17 L-6 9 L-4 20 Q-2 23 0 19 L0 9 L2 20 Q5 23 6 19 L5 8 L8 17 Q11 19 12 15 L11 3 Q16 1 16 -4 Q16 -11 9 -14 Q1 -17 -7 -14Z" fill="url(#skin)" stroke="#664c49" stroke-width="2"/>'
            '<path d="M-6 5 L-6 10 M0 5 L0 10 M5 4 L5 9" fill="none" stroke="#a56457" stroke-width="1.2"/></g>')


def person(x,ground,scale,role='hero',t=0,walk=0,phase=0,pose='idle',
           gesture=0,emotion=0,look=0,lean=0,talk=0,sit=0):
    """Articulated character: hips, knees, ankles, elbows, hands, eyes and mouth."""
    bob=abs(math.sin(phase))*4*walk + math.sin(t*2.0)*1.0*(1-walk)
    step=math.sin(phase)*29*walk
    lift_l=max(0,math.sin(phase))*15*walk
    lift_r=max(0,-math.sin(phase))*15*walk
    z=[f'<g transform="translate({n(x)} {n(ground)}) scale({n(scale)})">',
       '<ellipse cx="0" cy="4" rx="77" ry="13" fill="#14232b" opacity=".20"/>',
       f'<g transform="translate(0 {n(-bob)})">']
    # The knees articulate into a genuine sitting pose instead of a dangling
    # standing figure. The ankles also lag behind the arc of the swing.
    for side in (-1,1):
        stride=step if side==1 else -step
        lift=lift_r if side==1 else lift_l
        hip=(side*43,-258)
        stand_ankle=(side*47+stride,-30-lift)
        stand_knee=(mix(hip[0],stand_ankle[0],.54)+side*2,
                    mix(hip[1],stand_ankle[1],.53)-5*walk)
        swing_knee=(-3,-247) if side==-1 else (86,-247)
        swing_ankle=(8+math.sin(phase)*11,-76) if side==-1 else (98+math.sin(phase)*11,-76)
        knee=pt(stand_knee,swing_knee,sit)
        ankle=pt(stand_ankle,swing_ankle,sit)
        z.append(art.capsule(hip,knee,47,39,'url(#pants)'))
        z.append(art.capsule(knee,ankle,40,31,'url(#pants)'))
        shoeangle=mix(-stride*.12,-7+math.sin(phase)*6,sit)
        z.append(f'<g transform="translate({n(ankle[0])} {n(ankle[1]+12)}) rotate({n(shoeangle)})"><path d="M-21 -9 Q-17 -14 -10 -12 L12 -9 Q19 -5 27 1 L30 8 Q30 13 25 14 L-23 14 Q-29 11 -27 5Z" fill="#d9dfdc" stroke="#59686a" stroke-width="2.2"/><path d="M-27 8 Q0 11 29 8 L29 13 Q2 17 -26 13Z" fill="#f5f2e9"/><path d="M4 -7 L12 -5 M-2 -5 L8 -3" stroke="#a1ada8" stroke-width="1.3"/></g>')
    roll=lean+math.sin(phase)*2*walk+math.sin(t*1.8)*.35*(1-walk)
    z.append(f'<g transform="rotate({n(roll)} 0 -250)">')
    sw=math.sin(phase)*22*walk
    ls=(-103,-433); le=(-121-sw*.3,-343); lh=(-110-sw*.55,-277)
    rs=(103,-433); re=(121+sw*.3,-343); rh=(110+sw*.55,-277)
    if sit:
        le=pt(le,(-115,-450),sit); lh=pt(lh,(-71,-525),sit)
        re=pt(re,(115,-450),sit); rh=pt(rh,(71,-525),sit)
    elif pose=='knock':
        re=pt(re,(151,-414),gesture); rh=pt(rh,(220,-465),gesture)
    elif pose in ('question','gesture'):
        re=pt(re,(128,-364),gesture); rh=pt(rh,(181,-405),gesture)
    elif pose=='warn':
        # The near arm crosses the torso toward the person being addressed.
        re=pt(re,(50,-400),gesture); rh=pt(rh,(-100,-420),gesture)
    elif pose=='attack':
        re=pt(re,(176,-485),gesture); rh=pt(rh,(249,-516),gesture)
    elif pose=='defend':
        le=pt(le,(-130,-439),gesture); lh=pt(lh,(-56,-510),gesture)
        re=pt(re,(130,-439),gesture); rh=pt(rh,(56,-510),gesture)
    elif pose=='think':
        re=pt(re,(119,-370),gesture); rh=pt(rh,(38,-496),gesture)
    elif pose=='mediate':
        le=pt(le,(-133,-407),gesture); lh=pt(lh,(-175,-420),gesture)
        re=pt(re,(133,-407),gesture); rh=pt(rh,(175,-420),gesture)
    elif pose=='reconcile':
        if role=='mom':
            re=pt(re,(124,-370),gesture); rh=pt(rh,(145,-372),gesture)
        elif role=='dad':
            le=pt(le,(-124,-361),gesture); lh=pt(lh,(-145,-350),gesture)
    elif pose=='strike':
        re=pt(re,(156,-429),gesture); rh=pt(rh,(225,-458),gesture)
    sleeve=('url(#hoodie)' if role in ('hero','child') else
            ('url(#skin)' if role=='man' else {'woman':'#ad7877','mom':'#b68380','dad':'#755358','uncle':'#777566'}.get(role,'#667b80')))
    hand=art.hand if (role=='man' or sit>.5 or pose in ('knock','strike','attack')) else relaxed_hand
    def draw_hand(hand_fn,coords,angle):
        return hand_fn(*coords,angle=angle)
    z.append(art.arm(ls,le,lh,sleeve))
    if role=='man': z.append(tattoo(le,lh))
    z.append(draw_hand(hand,lh,-4))
    z.append('<path d="M-25 -503 L-25 -455 Q0 -437 25 -455 L25 -503Z" fill="url(#skin)" stroke="#71504c" stroke-width="2"/>')
    z.append(shirt(role))
    z.append(face(role,emotion,look,t,talk,tilt=lean*.6))
    # A raised protective arm belongs in front of the face, not behind the torso.
    if pose=='defend' and gesture>.05:
        z.append(art.arm(ls,le,lh,sleeve)+draw_hand(relaxed_hand,lh,18))
    z.append(art.arm(rs,re,rh,sleeve))
    if role=='man': z.append(tattoo(re,rh))
    z.append(draw_hand(hand,rh,-35 if pose=='question' else 5))
    z.append('</g></g></g>')
    return ''.join(z)


def moon_and_sky(t):
    twinkle=.6+.25*math.sin(t*1.4)
    return ('<rect width="540" height="960" fill="url(#nightSky)"/>'
            '<circle cx="425" cy="115" r="44" fill="#e3dfc4" opacity=".85"/>'
            '<circle cx="442" cy="104" r="41" fill="#17293a"/>'
            +''.join(f'<circle cx="{x}" cy="{y}" r="{r}" fill="#e7f1e5" opacity="{n(twinkle)}"/>' for x,y,r in [(50,90,1.5),(134,64,1.7),(252,122,1),(327,50,1.5),(501,166,1.2)])
            +'<path d="M0 285 L45 238 L75 259 L115 224 L159 273 L211 234 L260 284 V555 H0Z" fill="#1b303c" opacity=".6"/>')


def building(x=0,y=0,scale=1,light_window=False):
    a=[f'<g transform="translate({x} {y}) scale({scale})">',
       '<path d="M25 160 H518 V744 H25Z" fill="url(#apartment)" stroke="#273a43" stroke-width="4"/>',
       '<path d="M16 148 H527 V170 H16Z" fill="#71827d"/>',
       '<path d="M25 320 H518 M25 476 H518 M25 632 H518" stroke="#9aa7a0" opacity=".22" stroke-width="3"/>']
    for row in range(3):
        for col in range(4):
            xx=58+col*111; yy=196+row*153
            fill='#c6b58d' if ((row*4+col)%3==1) else '#263e49'
            a.append(f'<rect x="{xx}" y="{yy}" width="70" height="95" rx="2" fill="#283d45" stroke="#788a85" stroke-width="3"/><rect x="{xx+6}" y="{yy+6}" width="58" height="83" fill="{fill}"/><path d="M{xx+35} {yy+6} V{yy+89} M{xx+6} {yy+47} H{xx+64}" stroke="#647a78" stroke-width="3"/>')
    # Ground-floor entrance.
    a.extend(['<rect x="65" y="566" width="120" height="178" fill="#273b42" stroke="#87948b" stroke-width="4"/>',
              '<rect x="73" y="574" width="104" height="164" fill="#556f70"/>',
              '<rect x="84" y="587" width="82" height="71" fill="#344e59"/>',
              '<circle cx="156" cy="690" r="3" fill="#e4c482"/>',
              '</g>'])
    return ''.join(a)


def lamp(x=445,y=0):
    return (f'<g transform="translate({x} {y})"><path d="M0 310 V758" stroke="#304a50" stroke-width="8"/>'
            '<path d="M-32 307 Q0 289 32 307 L26 326 H-26Z" fill="#e7d4a7" stroke="#385050" stroke-width="3"/>'
            '<circle cx="0" cy="322" r="102" fill="url(#lampGlow)"/></g>')


def swing_frame():
    return ('<path d="M95 285 H284 M103 285 L48 771 M276 285 L320 771" fill="none" stroke="#586f72" stroke-width="9" stroke-linecap="round"/>'
            '<path d="M95 285 H284" fill="none" stroke="#b7bdb0" opacity=".55" stroke-width="3"/>')


def apartment_window(t):
    # A lit, distant window is treated as a comic-panel cutaway. A non-graphic
    # blow and recoil are animated explicitly; it is not just two talking figures.
    attack=smooth(8.85,9.35,t)*(1-smooth(9.50,9.90,t))
    recoil=smooth(9.40,9.62,t)*(1-smooth(10.00,10.65,t))
    defend=.12+.78*smooth(9.35,9.92,t)
    agitated=.25+.13*math.sin(t*4.0)
    a=['<rect x="292" y="186" width="236" height="303" rx="8" fill="#111f2a" opacity=".35"/>',
       '<rect x="300" y="194" width="220" height="287" rx="5" fill="#253841" stroke="#a2afa2" stroke-width="6"/>',
       '<rect x="309" y="203" width="202" height="269" fill="url(#warmRoom)"/>',
       '<path d="M309 430 H511 V472 H309Z" fill="#8e7769"/>',
       '<path d="M318 220 Q350 212 383 220 M438 220 Q470 212 501 220" fill="none" stroke="#fff2d3" opacity=".24" stroke-width="3"/>']
    a.append(person(363,465,.34,'man',t=t,pose='attack' if attack>.005 else 'gesture',
                    gesture=attack if attack>.005 else agitated,emotion=.95,look=4,
                    lean=-3+6*attack,talk=speech_amp('man',t)))
    a.append(person(454+6*recoil,465,.33,'woman',t=t,pose='defend',gesture=defend,
                    emotion=.85,look=-4,lean=3+10*recoil,talk=speech_amp('woman',t)))
    if 9.32<t<9.57:
        flash=1-abs(t-9.445)/.125
        a.append(f'<path d="M439 274 l4 9 10 -3 -6 8 7 7 -10 -1 -4 9 -2 -10 -10 -1 8 -5 -4 -9 7 4Z" fill="#fff0bf" opacity="{n(clamp(flash))}"/>')
    a.extend(['<path d="M410 203 V472 M309 318 H511" stroke="#6a6c63" stroke-width="5" opacity=".55"/>',
              '<path d="M316 209 H350 L316 250Z" fill="#fff4d5" opacity=".16"/>'])
    return ''.join(a)


def exit_scene(t):
    progress=smooth(.65,5.15,t)
    # Start within the doorway and grow toward camera, not at giant scale behind it.
    x=mix(103,262,progress); ground=mix(784,822,progress)
    scale=mix(.27,.70,progress)
    walk=smooth(.65,1.05,t)*(1-smooth(4.9,5.55,t))
    op=smooth(.0,.45,t)*(1-smooth(1.55,2.45,t)); width=104*(1-.72*op)
    a=[moon_and_sky(t),building(-20,50,1),lamp(445),
       '<path d="M0 788 Q220 755 540 788 V960 H0Z" fill="url(#court)"/>',
       '<path d="M0 842 H540 M0 900 H540" stroke="#a4ada2" opacity=".18" stroke-width="2"/>',
       '<path d="M350 472 H525 M364 472 L330 782 M511 472 L535 782" fill="none" stroke="#5d7473" stroke-width="8"/>',
       '<path d="M392 473 V665 M484 473 V665" fill="none" stroke="#9aa9a0" stroke-width="3"/><path d="M388 667 H488" stroke="#92765e" stroke-width="8"/>',
       f'<path d="M53 624 L{n(53+width)} {n(624+8*op)} L{n(53+width)} 786 H53Z" fill="#6e8783" stroke="#354e54" stroke-width="3"/>',
       '<path d="M53 782 H171 V790 H53Z" fill="#a6b5a9"/>']
    a.append(person(x,ground,scale,'hero',t=t,walk=walk,phase=t*8.4,look=1,lean=-.5))
    return ''.join(a)


def courtyard_scene(t):
    # The swing, chains and rider are separate articulated pieces. As he hears
    # the cries he stops and steps off; later he hesitates with a hand to his chin.
    a=[moon_and_sky(t),building(-18,43,1),
       '<path d="M0 780 Q240 743 540 780 V960 H0Z" fill="url(#court)"/>',
       '<path d="M0 866 H540 M0 925 H540" stroke="#a4ada2" opacity=".12" stroke-width="2"/>',
       apartment_window(t),swing_frame()]
    stop=smooth(11.5,12.45,t)
    angle=8.5*math.sin((t-5.7)*2.15)*(1-stop)
    dismount=smooth(12.05,12.95,t)
    sit=1-dismount
    x=mix(185,137,dismount); ground=mix(800,818,dismount)
    thinking=smooth(15.4,16.2,t)*(1-smooth(19.1,19.8,t))
    a.append(f'<g transform="rotate({n(angle)} 185 285)"><path d="M135 288 L135 618 M235 288 L235 618" stroke="#a9b5ae" stroke-width="3"/>')
    seat='<path d="M124 621 Q185 628 246 621 L244 632 Q185 638 126 632Z" fill="#967255" stroke="#33484a" stroke-width="3"/>'
    if dismount>.65: a.append(seat)  # once he gets off, the seat stays behind him
    a.append(person(x,ground,.70,'hero',t=t,walk=(1-smooth(12.25,12.95,t))*dismount,
                    phase=(t-5.7)*3.3,pose='think' if thinking>.01 and not sit else 'idle',
                    gesture=thinking,sit=sit,emotion=.35+.40*stop,look=4,lean=-2.4*stop))
    if dismount<=.65: a.append(seat)  # but it is in front of his hips while seated
    a.append('</g>')
    return ''.join(a)


def memory_scene(t):
    local=t-20.0
    peace=smooth(6.0,7.0,local)
    arguing=1-smooth(4.9,6.1,local)
    uncle=mix(620,434,smooth(3.55,4.85,local))
    walk=smooth(3.55,3.8,local)*(1-smooth(4.55,4.9,local))
    mediating=smooth(4.55,5.15,local)*(1-smooth(7.2,8.5,local))
    a=['<rect width="540" height="960" fill="url(#warmRoom)"/>',
       '<path d="M0 660 H540 V960 H0Z" fill="#a58772"/>',
       '<path d="M0 652 H540 V664 H0Z" fill="#d0b497" opacity=".8"/>',
       '<rect x="32" y="205" width="140" height="180" fill="#e6d2af" stroke="#927c6c" stroke-width="5"/><rect x="42" y="215" width="120" height="160" fill="#97aba1"/><path d="M102 215 V375 M42 293 H162" stroke="#e1d3b7" stroke-width="5"/>',
       '<path d="M31 203 Q39 271 36 386 L50 386 Q54 279 44 203 M160 203 Q150 276 154 386 L169 386 Q168 277 173 203" fill="#ddc4a5" opacity=".8"/>',
       '<rect x="461" y="222" width="78" height="438" fill="#695b55" stroke="#a28976" stroke-width="6"/><path d="M470 228 H532 V660 H470Z" fill="#8a7867"/><circle cx="482" cy="470" r="3" fill="#d6bc8c"/>',
       '<rect x="121" y="468" width="301" height="136" rx="25" fill="#a48572" stroke="#765f58" stroke-width="4"/><path d="M135 505 H409 M230 474 V504 M318 474 V504" stroke="#dfc1a3" opacity=".27" stroke-width="3"/>',
       '<path d="M0 746 H540 M0 841 H540" stroke="#dfc4a5" opacity=".25" stroke-width="2"/>']
    # The parents argue, then the uncle comes in, opens his hands, and they
    # turn to each other and hold hands. All have their own moving skeleton.
    mom_pose='reconcile' if peace>.01 else 'question'
    dad_pose='reconcile' if peace>.01 else 'warn'
    mom_g=peace if peace>.01 else arguing*(.65+.22*math.sin(local*5))
    dad_g=peace if peace>.01 else arguing*(.65+.22*math.sin(local*5+1.8))
    a.append(person(180,700,.47,'mom',t=t,pose=mom_pose,gesture=mom_g,
                    emotion=.7*arguing,look=3,lean=3*arguing,
                    talk=arguing*max(0,math.sin(local*8))))
    a.append(person(318,700,.50,'dad',t=t,pose=dad_pose,gesture=dad_g,
                    emotion=.8*arguing,look=-3,lean=-3*arguing,
                    talk=arguing*max(0,math.sin(local*8+2.4))))
    if peace>.01:
        a.append(f'<g opacity="{n(peace)}"><path d="M226 513 Q234 524 245 526" fill="none" stroke="#b68380" stroke-width="12" stroke-linecap="round"/><path d="M269 510 Q259 522 251 526" fill="none" stroke="#755358" stroke-width="12" stroke-linecap="round"/><ellipse cx="248" cy="526" rx="8" ry="6" fill="#d89f81" stroke="#8d6559" stroke-width="1.5"/></g>')
    a.append(person(uncle,710,.49,'uncle',t=t,walk=walk,phase=local*9,
                    pose='mediate',gesture=mediating,look=-4,emotion=.1,lean=-2*mediating,
                    talk=mediating*max(0,math.sin(local*6))))
    a.append(person(68,805,.40,'child',t=t,emotion=.6*arguing,look=3,lean=-3*arguing))
    # Warm, slightly desaturated treatment separates the past from the present.
    a.append('<rect width="540" height="960" fill="url(#memoryGlow)"/>')
    a.append('<rect x="159" y="52" width="222" height="36" rx="18" fill="#51443d" opacity=".7"/>')
    a.append(text(270,76,'ВОСПОМИНАНИЕ',14,700,'#f6ead3'))
    return ''.join(a)


def stairs_scene(t):
    progress=smooth(29.0,35.8,t)
    x=mix(105,421,progress); ground=mix(810,610,progress)
    walk=1-smooth(35.1,36.0,t)
    a=['<rect width="540" height="960" fill="url(#hall)"/>',
       '<path d="M0 0 H540 V540 L0 720Z" fill="#a3a99f" opacity=".32"/>',
       '<path d="M0 865 H540 V960 H0Z" fill="#425658"/>',
       '<path d="M0 813 H60 V780 H120 V747 H180 V714 H240 V681 H300 V648 H360 V615 H420 V582 H480 V549 H540 V960 H0Z" fill="#647473" stroke="#405557" stroke-width="4"/>',
       '<path d="M0 813 H60 M60 780 H120 M120 747 H180 M180 714 H240 M240 681 H300 M300 648 H360 M360 615 H420 M420 582 H480 M480 549 H540" stroke="#bcc5b6" stroke-width="5"/>',
       '<path d="M15 622 L520 343 M55 608 V779 M165 548 V718 M275 487 V657 M385 427 V596 M495 366 V537" fill="none" stroke="#3c5153" stroke-width="7"/>',
       '<circle cx="106" cy="139" r="95" fill="url(#lampGlow)"/><path d="M80 105 H130 L125 137 H85Z" fill="#ead9aa" stroke="#63746d" stroke-width="3"/>']
    a.append(person(x,ground,.62,'hero',t=t,walk=walk,phase=(t-29)*9,look=2,lean=2.5))
    return ''.join(a)


def hall_scene(t):
    # Door, neighbor, hero and broken splinters are separate animated layers.
    open_normal=smooth(38.20,39.0,t)*(1-smooth(47.72,48.08,t))
    damage=smooth(53.72,53.90,t)
    forced=smooth(53.84,54.28,t)
    opened=max(open_normal,forced)
    width=190*(1-.76*opened)
    approach=smooth(52.85,53.70,t)
    entry=smooth(54.20,55.75,t)
    hx=mix(154+42*approach,383,entry)
    scale=mix(.72,.54,entry)
    knock=smooth(36.90,37.12,t)*(1-smooth(38.0,38.25,t))
    if knock>0: knock*=.9+.1*math.cos((t-37.12)*math.pi*2/.34)
    question=smooth(41.0,41.55,t)*(1-smooth(43.75,44.12,t))
    strike=smooth(53.27,53.70,t)*(1-smooth(54.03,54.40,t))
    warning=smooth(44.18,44.75,t)*(1-smooth(46.85,47.60,t))
    a=['<rect width="540" height="960" fill="url(#hall)"/>',
       '<path d="M0 790 H540 V960 H0Z" fill="#647675"/>',
       '<path d="M0 842 H540 M0 912 H540 M150 790 L105 960 M410 790 L475 960" stroke="#a9b5a8" stroke-width="2" opacity=".32"/>',
       '<path d="M0 111 H540 M0 280 H540 M0 776 H280" stroke="#d6d7bf" opacity=".2" stroke-width="3"/>',
       '<circle cx="95" cy="145" r="100" fill="url(#lampGlow)"/><path d="M70 103 H119 L114 133 H75Z" fill="#ebdbad" stroke="#64746d" stroke-width="3"/>',
       '<rect x="293" y="194" width="220" height="610" rx="4" fill="#344044" stroke="#697b76" stroke-width="7"/>',
       '<rect x="305" y="205" width="194" height="590" fill="#705a50"/>',
       '<path d="M305 700 H499 V795 H305Z" fill="#594c49"/>']
    if 38.20<t<48.10:
        # Clipping, rather than fading a person away, makes the slam physically
        # conceal him behind the moving door.
        a.append('<clipPath id="doorClip"><rect x="305" y="205" width="194" height="590"/></clipPath><g clip-path="url(#doorClip)">')
        a.append(person(415,796,.70,'man',t=t,emotion=.85,look=-4,pose='warn',gesture=warning,
                        talk=speech_amp('man',t),lean=-1-2*warning))
        a.append('</g>')
    # The leaf rotates on its left hinge; after the strike it has a punched hole
    # with cracks and a torn edge, and is shoved back into the room.
    a.append(f'<g transform="translate(305 205) scale({n(width/190)} 1)">')
    a.append('<path d="M0 0 H190 V590 H0Z" fill="url(#wood)" stroke="#3c4543" stroke-width="4"/>')
    a.append('<path d="M10 45 H170 M10 300 H170 M10 490 H170" stroke="#d6aa84" opacity=".32" stroke-width="2"/>')
    a.append('<circle cx="162" cy="288" r="5" fill="#d7bd84"/>')
    if damage>0:
        a.append(f'<g opacity="{n(damage)}"><path d="M36 235 l14 -10 9 8 16 -9 9 17 18 2 -8 15 8 13 -18 3 -9 18 -15 -11 -16 9 -4 -17 -17 -5 13 -13 -5 -11Z" fill="#26383b" stroke="#d6a77b" stroke-width="4" stroke-linejoin="round"/>')
        a.append('<path d="M39 238 l-18 -21 -6 -28 M91 246 l27 -19 9 -30 M43 272 l-22 24 -3 25 M88 274 l24 19 12 28" fill="none" stroke="#d8b58d" stroke-width="3"/></g>')
    a.append('</g>')
    a.append('<path d="M293 198 V802 M511 198 V802 M293 198 H511 M285 802 H520" fill="none" stroke="#8b9a91" stroke-width="7"/>')
    if damage>0:
        # Splinters fly, then settle near the threshold instead of disappearing.
        flight=clamp((t-53.76)/1.15)
        for i in range(7):
            xx=349+(-1 if i%2 else 1)*(18+i*8)*flight
            yy=463-(32+i*9)*math.sin(math.pi*flight)+325*flight
            theta=(i-3)*17+flight*(95+i*16)
            a.append(f'<path d="M-10 -3 L11 -2 L4 3 L-8 3Z" transform="translate({n(xx)} {n(yy)}) rotate({n(theta)})" fill="#d2ae85" stroke="#5a4d43" stroke-width="1" opacity="{n(damage)}"/>')
    pose='strike' if strike>.01 else ('knock' if knock>.01 else ('question' if question>.01 else 'idle'))
    gesture=strike if strike>.01 else (knock if knock>.01 else question)
    a.append(person(hx,800,scale,'hero',t=t,walk=(.45*approach*(1-entry)+entry*(1-smooth(55.2,55.75,t))),
                    phase=t*8.4,pose=pose,gesture=gesture,emotion=.40 if t<47.7 else .95,
                    look=4,lean=(-8*strike-1.5),talk=speech_amp('hero',t) if 41.0<t<44 else 0))
    return ''.join(a)


def title_scene(t):
    appear=smooth(56.0,56.8,t)
    return ('<rect width="540" height="960" fill="#0d1722"/>'
            '<circle cx="270" cy="390" r="240" fill="url(#blueglow)" opacity=".18"/>'
            f'<g opacity="{n(appear)}">'
            +text(270,381,'ПРОДОЛЖЕНИЕ СЕРИАЛА',17,700,'#b9c6c4')
            +text(270,446,'«ВМЕШАТЬСЯ»',36,700,'#f3f4e9')
            +text(270,499,'СЛЕДУЕТ…',24,700,'#e4bd74')
            +text(270,793,'ЗВУК: OCULUS AUDIO PACK 01 — OCULUS VR, LLC (ИЗМЕНЕНО)',10,400,'#aab8ba')
            +text(270,811,'developers.meta.com/vr/downloads/package/oculus-audio-pack-1/',9,400,'#aab8ba')
            +text(270,828,'CC BY 4.0 · creativecommons.org/licenses/by/4.0/',10,400,'#aab8ba')+'</g>')


CAPTIONS=[
 (0.45,2.25,['НОЧЬЮ Я ВЫШЕЛ ИЗ КВАРТИРЫ']),
 (2.25,3.98,['И СЕЛ НА КАЧЕЛИ ВО ДВОРЕ.']),
 (6.10,8.70,['ЗАМОЛЧИ! СЛЫШИШЬ?']),
 (8.70,9.65,['ЗАМОЛЧИ!']),
 (9.70,11.70,['НЕТ! ХВАТИТ!','НЕ ТРОГАЙ МЕНЯ!']),
 (11.70,12.58,['ПОМОГИТЕ!']),
 (13.00,15.45,['ИЗ ОКНА НАПРОТИВ','ДОНОСИЛИСЬ КРИКИ.']),
 (15.45,17.65,['Я РАЗОЗЛИЛСЯ, НО ОСТАНОВИЛСЯ.']),
 (17.65,19.39,['МОЖЕТ, ЭТО НЕ МОЁ ДЕЛО?']),
 (20.25,23.25,['Я ВСПОМНИЛ, КАК В ДЕТСТВЕ','РУГАЛИСЬ МОИ РОДИТЕЛИ.']),
 (23.50,25.10,['ОДНАЖДЫ К НАМ ЗАШЁЛ ДЯДЯ,']),
 (25.10,27.60,['ПОГОВОРИЛ С НИМИ,','И ОНИ ПОМИРИЛИСЬ.']),
 (29.60,32.80,['ТОГДА Я РЕШИЛ ПОДНЯТЬСЯ','К СОСЕДЯМ И ПОСТУЧАТЬ.']),
 (39.50,40.50,['ЧЁ НАДО?']),
 (41.15,43.70,['ЧТО ЗА КРИКИ?','МОГУ ЛИ Я ВМЕШАТЬСЯ?']),
 (44.25,47.65,['СЛЫШИШЬ, ПАРЕНЬ,','УХОДИ ОТСЮДА ПО-ДОБРОМУ.']),
 (48.75,52.60,['ДВЕРЬ ЗАХЛОПНУЛАСЬ.','Я РАЗОЗЛИЛСЯ И РЕШИЛ ВОЙТИ.']),
]


def captions(t):
    for start,end,lines in CAPTIONS:
        if start<=t<end:
            # The protagonist is always visible from head to toe. Captions stay
            # in the upper safe area instead of covering the shoes or face.
            size=18
            y=134 if len(lines)==1 else 122
            panel_y=105 if len(lines)==1 else 96
            a=[f'<rect x="27" y="{panel_y}" width="486" height="{43 if len(lines)==1 else 67}" rx="10" fill="#0b1720" opacity=".83"/>']
            for i,line in enumerate(lines):
                a.append(text(270,y+i*24,line,size,700,'#fbfcf5'))
            return ''.join(a)
    return ''


def frame_svg(t):
    if t<5.8: body=exit_scene(t)
    elif t<20.0: body=courtyard_scene(t)
    elif t<29.0: body=memory_scene(t)
    elif t<36.5: body=stairs_scene(t)
    elif t<56.0: body=hall_scene(t)
    else: body=title_scene(t)
    # A gentle virtual-camera push adds tension without ever cropping the hero.
    # It transforms vector geometry, not a still image or a photo.
    if 5.8<=t<20:
        zoom=1+.025*smooth(6,18,t)
    elif 36.5<=t<56:
        zoom=1+.035*smooth(36.5,47,t)*(1-smooth(51.6,53.1,t))
    else:
        zoom=1
    if zoom!=1:
        body=f'<g transform="translate(270 500) scale({n(zoom)}) translate(-270 -500)">{body}</g>'
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">'
            +art.DEFS+EXTRA_DEFS+body+captions(t)
            +'<rect width="540" height="960" fill="url(#vig)" pointer-events="none"/></svg>')


def frame_png(t,w=RENDER_W,h=RENDER_H):
    return resvg_py.svg_to_bytes(svg_string=frame_svg(t),width=w,height=h,
                                 skip_system_fonts=True,font_files=FONT_FILES)


def decode_ogg(path,sr=44100):
    data=subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(),'-v','error','-i',str(path),'-f','f32le','-ac','2','-ar',str(sr),'-'],stdout=subprocess.PIPE,check=True).stdout
    return np.frombuffer(data,dtype='<f4').reshape(-1,2).astype(np.float32)


def audio_mix():
    sr=44100; count=sr*DURATION
    t=np.arange(count,dtype=np.float32)/sr
    track=np.zeros((count,2),dtype=np.float32)
    rng=np.random.default_rng(341)
    def add(start,signal,vol=1,pan=0):
        i=max(0,int(start*sr)); length=min(len(signal),count-i)
        if length<=0: return
        if signal.ndim==1:
            track[i:i+length,0]+=signal[:length]*vol*(1-.35*pan)
            track[i:i+length,1]+=signal[:length]*vol*(1+.35*pan)
        else:
            track[i:i+length,0]+=signal[:length,0]*vol*(1-.35*pan)
            track[i:i+length,1]+=signal[:length,1]*vol*(1+.35*pan)
    # Air is band-limited (rather than a DC random walk) and very quiet indoors.
    noise=rng.normal(0,1,count).astype(np.float32)
    window=64
    csum=np.cumsum(np.pad(noise,(window,0)),dtype=np.float64)
    wind=((csum[window:]-csum[:-window])/window).astype(np.float32)*.047
    indoor=np.where(t<20,1.0,np.where(t<29,.20,.32)).astype(np.float32)
    gust=(.75+.20*np.sin(2*np.pi*.09*t)).astype(np.float32)
    add(0,wind*indoor*gust)
    # Real field-recorded night insects and distant city ambience, CC BY 4.0.
    # The courtyard mix is faded at both ends; interior scenes have no insects.
    courtyard_len=int(20.0*sr)
    amb_fade=np.minimum(1,np.arange(courtyard_len)/(sr*.6))*np.minimum(1,(courtyard_len-np.arange(courtyard_len))/(sr*.8))
    amb_fade=amb_fade.astype(np.float32)[:,None]
    night=decode_ogg(SOUND_DIR/'AMBForst_Night_LOOP_01.ogg',sr)[:courtyard_len]
    city=decode_ogg(SOUND_DIR/'AMBUrbn_CityAmerican_LOOP_01.ogg',sr)[:courtyard_len]
    add(0,night*amb_fade,.30)
    add(0,city*amb_fade,.035)
    # Understated, changing drone supports the story without masking the voices.
    pitches=[110,103.83,98,110,130.81,123.47,110,103.83,98,110,98]
    for k,start in enumerate(np.arange(0,56,5.5)):
        duration=min(6.4,56-start); u=np.arange(int(sr*duration),dtype=np.float32)/sr
        env=np.minimum(1,u/.8)*np.minimum(1,(duration-u)/1.1)
        root=pitches[k%len(pitches)]
        chord=(np.sin(2*np.pi*root*u)+.28*np.sin(2*np.pi*root*1.5*u)+.14*np.sin(2*np.pi*root*2*u))*env
        add(start,chord,.019)
    # Selected voices: normalize each take to a shared target without clipping.
    for name,start,role,distant in VOICES:
        signal,sr0=voice_data(name)
        if sr0!=sr: raise ValueError(f'Unexpected sample rate in {name}: {sr0}')
        rms=float(np.sqrt(np.mean(signal*signal))) or 1
        gain=min(.14/rms, .76/(float(np.max(np.abs(signal)))+1e-6))
        signal=signal*gain
        if distant:
            # Soften the upper frequencies and add a restrained wall reflection.
            signal=np.convolve(signal,np.ones(7,dtype=np.float32)/7,mode='same')
            delayed=np.pad(signal,(int(.07*sr),0))[:len(signal)]
            signal=.72*signal+.18*delayed
        add(start,signal,.72 if distant else 1.0,.33 if distant else 0)
    # Foley from CC0 packs, timed to the keyframed action.
    fs0=decode_ogg(FOLEY_DIR/'footstep_concrete_000.ogg',sr)
    fs1=decode_ogg(FOLEY_DIR/'footstep_concrete_003.ogg',sr)
    wooden=decode_ogg(SOUND_DIR/'footstep_wood_002.ogg',sr)
    creak=decode_ogg(SOUND_DIR/'creak1.ogg',sr)
    close=decode_ogg(SOUND_DIR/'doorClose_4.ogg',sr)
    opening=decode_ogg(FOLEY_DIR/'doorOpen_1.ogg',sr)
    latch=decode_ogg(FOLEY_DIR/'metalLatch.ogg',sr)
    knock=decode_ogg(SOUND_DIR/'impactWood_light_001.ogg',sr)
    heavy=decode_ogg(SOUND_DIR/'impactWood_heavy_002.ogg',sr)
    plank=decode_ogg(SOUND_DIR/'impactPlank_medium_001.ogg',sr)
    punch=decode_ogg(SOUND_DIR/'impactPunch_medium_001.ogg',sr)
    add(.18,opening,.12,-.3)
    for j,when in enumerate([1.0,1.48,1.96,2.44,2.92,3.40,3.88,4.36,4.84,5.32]):
        add(when,fs0 if j%2==0 else fs1,.15,-.2)
    for when in (6.4,7.85,9.30,10.75): add(when,creak,.09,-.25)
    add(9.40,punch,.095,.50)  # the distant blow, deliberately non-graphic
    for when in (23.9,24.3,24.65): add(when,wooden,.085,.35)
    for j,when in enumerate(np.arange(29.7,35.8,.43)):
        foot=fs0 if j%2==0 else fs1
        add(float(when),foot,.14,(-.3 if j%2 else .3))
        add(float(when)+.08,foot,.035,.2)  # a little stairwell reflection
    for when in (37.12,37.46,37.80): add(when,knock,.27,.38)
    add(38.45,opening,.15,.35)
    add(47.90,close,.70,.35)
    add(53.70,heavy,.70,.25)
    add(53.76,plank,.55,.25)
    add(53.78,latch,.18,.25)
    add(54.85,wooden,.14,.15); add(55.25,wooden,.14,.15)
    fade=np.minimum(1,t/.07)*np.minimum(1,(DURATION-t)/.35)
    track*=fade[:,None]
    peak=float(np.max(np.abs(track)))
    if peak>.93: track*=.93/peak
    return (track*32767).astype('<i2'),sr


def write_wav(path):
    samples,sr=audio_mix()
    with wave.open(str(path),'wb') as f:
        f.setnchannels(2); f.setsampwidth(2); f.setframerate(sr); f.writeframes(samples.tobytes())


def render(output=OUT, width=RENDER_W, height=RENDER_H):
    output.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='vmeshat-') as tmp:
        wav=Path(tmp)/'mix.wav'; write_wav(wav)
        cmd=[imageio_ffmpeg.get_ffmpeg_exe(),'-hide_banner','-loglevel','error','-y',
             '-f','image2pipe','-vcodec','png','-framerate',str(FPS),'-i','-',
             '-i',str(wav),'-t',str(DURATION),'-vf',f'scale={OUTPUT_W}:{OUTPUT_H}:flags=lanczos',
             '-c:v','libx264','-preset','veryfast','-crf','20','-pix_fmt','yuv420p',
             '-c:a','aac','-b:a','192k','-movflags','+faststart',str(output)]
        p=subprocess.Popen(cmd,stdin=subprocess.PIPE)
        try:
            for i in range(FPS*DURATION):
                p.stdin.write(frame_png(i/FPS,width,height))
                if i%(FPS*5)==0: print(f'{i//FPS:02d}s / {DURATION}s',flush=True)
        finally:
            p.stdin.close()
        if p.wait()!=0: raise RuntimeError('ffmpeg render failed')
    print(f'Complete: {output} ({output.stat().st_size/1_000_000:.1f} MB)',flush=True)


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--samples',action='store_true')
    ap.add_argument('--width',type=int,default=RENDER_W)
    ap.add_argument('--height',type=int,default=RENDER_H)
    ap.add_argument('--output',type=Path,default=OUT)
    args=ap.parse_args()
    if args.samples:
        folder=HERE/'previews'; folder.mkdir(parents=True,exist_ok=True)
        for t in (1,4,7,9.6,13.5,17,21.0,24.0,27.0,31,35,37.3,39.7,42,45.5,48.3,51,53.8,55,57.5):
            p=folder/f'frame_{t:.2f}.png'; p.write_bytes(frame_png(t,540,960)); print(p)
    else: render(args.output,args.width,args.height)

if __name__=='__main__': main()
