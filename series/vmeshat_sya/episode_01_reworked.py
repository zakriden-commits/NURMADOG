#!/usr/bin/env python3
"""«Вмешаться», эпизод 1: переработанная рисованная 2D-анимация.

The characters, backgrounds and props below are original hand-authored SVG
paths. Key poses, expressions, shot changes, timing and sound cues are edited
by hand; intermediate frames are interpolated. No still picture, 3D model, or
stock animation clip is used. The 2026 first version is kept separately.
"""
from __future__ import annotations
import argparse
import math
import subprocess
import sys
import tempfile
import wave
from functools import lru_cache
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import imageio_ffmpeg
import numpy as np
import resvg_py

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
sys.path.insert(0,str(HERE))
import rig_v2 as rig
import episode_01 as old

W,H=540,960
FPS=24
DURATION=60
RENDER_W,RENDER_H=1080,1920
OUTPUT_W,OUTPUT_H=1080,1920
OUTPUT=ROOT/'videos'/'vmeshat_sya_episode_01_reworked.mp4'
FONT_FILES=old.FONT_FILES
V1=HERE/'voices'
V2=HERE/'voices_v2'
SOUNDS=HERE/'sounds'
FOLEY=ROOT/'animation'/'sounds'
clamp=rig.clamp
mix=rig.lerp
n=rig.fmt
person=rig.person


def smooth(a,b,t):
    p=clamp((t-a)/(b-a));return p*p*(3-2*p)


def pulse(a,b,c,d,t): return smooth(a,b,t)*(1-smooth(c,d,t))


# Explicit editing sheet shared by picture, dialogue and subtitles.  The second
# take for 'witness' did not exist; the selected first take is retained instead.
VOICES=[
    (V2/'hero_01_night.wav',.15,'narrator'),
    (V2/'man_01_shouting.wav',6.85,'man_window'),
    (V2/'woman_01_help.wav',10.90,'woman_window'),
    (V1/'hero_02_witness.wav',14.20,'narrator'),
    (V2/'hero_03_memory.wav',20.65,'narrator'),
    (V2/'hero_04_decision.wav',32.85,'narrator'),
    (V1/'man_02_door.wav',39.00,'man'),
    (V2/'hero_05_question.wav',40.35,'hero'),
    (V2/'man_03_warning.wav',44.10,'man'),
    (V2/'hero_06_angry.wav',48.00,'narrator'),
]

DEFS='''<defs>
<linearGradient id="v2sky" x1="0" y1="0" x2="0" y2="1"><stop stop-color="#0a1626"/><stop offset=".58" stop-color="#263f4c"/><stop offset="1" stop-color="#43575b"/></linearGradient>
<linearGradient id="v2facade" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#536c6b"/><stop offset="1" stop-color="#263c48"/></linearGradient>
<linearGradient id="v2nightfloor" x1="0" y1="0" x2="0" y2="1"><stop stop-color="#465d60"/><stop offset="1" stop-color="#182c38"/></linearGradient>
<linearGradient id="v2hall" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#9aa9a4"/><stop offset=".55" stop-color="#6c8583"/><stop offset="1" stop-color="#455d65"/></linearGradient>
<linearGradient id="v2hallfloor" x1="0" y1="0" x2="0" y2="1"><stop stop-color="#6e8180"/><stop offset="1" stop-color="#273e48"/></linearGradient>
<linearGradient id="v2wood" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#9a735b"/><stop offset=".6" stop-color="#705345"/><stop offset="1" stop-color="#47393a"/></linearGradient>
<linearGradient id="v2warm" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#e8c7a2"/><stop offset=".6" stop-color="#b9927d"/><stop offset="1" stop-color="#836a67"/></linearGradient>
<linearGradient id="v2roomfloor" x1="0" y1="0" x2="0" y2="1"><stop stop-color="#a78370"/><stop offset="1" stop-color="#69545a"/></linearGradient>
<linearGradient id="v2window" x1="0" y1="0" x2="0" y2="1"><stop stop-color="#f6d7a4"/><stop offset="1" stop-color="#b6876f"/></linearGradient>
<radialGradient id="v2lamp"><stop stop-color="#ffdfa1" stop-opacity=".65"/><stop offset=".38" stop-color="#f1be7a" stop-opacity=".24"/><stop offset="1" stop-color="#e9ad74" stop-opacity="0"/></radialGradient>
<radialGradient id="v2lit"><stop stop-color="#f5d5a1" stop-opacity=".36"/><stop offset="1" stop-color="#f1c88c" stop-opacity="0"/></radialGradient>
<linearGradient id="v2vignette" x1="0" y1="0" x2="0" y2="1"><stop stop-color="#101e2c" stop-opacity=".26"/><stop offset=".22" stop-color="#101e2c" stop-opacity="0"/><stop offset=".78" stop-color="#101e2c" stop-opacity="0"/><stop offset="1" stop-color="#101e2c" stop-opacity=".38"/></linearGradient>
<pattern id="v2dots" width="11" height="11" patternUnits="userSpaceOnUse"><circle cx="1.4" cy="1.4" r=".65" fill="#e5f4e5" opacity=".18"/></pattern>
<clipPath id="v2winclip"><rect x="319" y="190" width="185" height="250" rx="2"/></clipPath>
<clipPath id="v2doorclip"><rect x="319" y="198" width="186" height="608"/></clipPath>
</defs>'''


def text(x,y,s,size=19,weight=700,fill='#f8f5eb',anchor='middle',extra=''):
    return old.text(x,y,s,size,weight,fill,anchor,extra)


@lru_cache(maxsize=32)
def voice(path): return old.load_wav(path)


def speech_amp(role,t):
    level=0.
    for path,start,kind in VOICES:
        if kind!=role: continue
        s,sr=voice(path);pos=int((t-start)*sr)
        if 0<=pos<len(s):
            v=s[max(0,pos-400):min(len(s),pos+400)]
            if len(v):level=max(level,min(1.,float(np.sqrt(np.mean(v*v)))*8))
    return level


def sky(t):
    a=['<rect width="540" height="960" fill="url(#v2sky)"/>',
       '<path d="M0 310 L43 268 L83 287 L126 239 L178 290 L232 264 L268 310 V470 H0Z" fill="#1c3241" opacity=".62"/>',
       '<circle cx="442" cy="111" r="36" fill="#e9e1bf" opacity=".83"/>',
       '<circle cx="456" cy="100" r="33" fill="#142638"/>']
    for j,(x,y,r) in enumerate([(42,95,1.2),(104,64,1.1),(211,124,1),(310,60,1.4),(382,174,1),(505,176,1.3),(262,91,.7)]):
        a.append(f'<circle cx="{x}" cy="{y}" r="{r}" fill="#e0eee6" opacity="{n(.58+.18*math.sin(t*1.3+j))}"/>')
    return ''.join(a)


def facade():
    # Receding masonry, deep window reveals and layered tree silhouettes.
    a=['<path d="M-25 245 L445 205 L568 267 L568 794 L-25 794Z" fill="url(#v2facade)" stroke="#253b43" stroke-width="5"/>',
       '<path d="M-25 245 L445 205 L568 267 L555 282 L445 225 L-25 266Z" fill="#87948b" opacity=".65"/>',
       '<path d="M440 224 L568 284 V794 H440Z" fill="#253b48" opacity=".44"/>',
       '<path d="M-10 403 L440 378 M-10 561 L440 547 M-10 719 L440 716" stroke="#cad1b9" opacity=".10" stroke-width="3"/>']
    for row in range(3):
        for col in range(3):
            x=19+col*123; y=288+row*155-col*8
            lit=(row*3+col)%4==1
            fill='#d7c199' if lit else '#263f4b'
            a.append(f'<path d="M{x} {y} l76 -4 v103 l-76 4Z" fill="#1d303a" stroke="#81948c" stroke-width="4"/><path d="M{x+6} {y+7} l64 -4 v89 l-64 4Z" fill="{fill}"/><path d="M{x+38} {y+5} v92 M{x+6} {y+53} l64 -4" stroke="#70867f" stroke-width="3" opacity=".75"/>')
    a.extend(['<path d="M-20 742 Q24 715 50 740 Q62 699 93 720 Q123 688 150 730 Q174 698 203 740 V813 H-20Z" fill="#263f48"/>',
       '<path d="M405 760 Q427 722 451 748 Q477 704 495 733 Q523 702 558 735 V813 H405Z" fill="#203b42"/>'])
    return ''.join(a)


def courtyard_floor():
    return ('<path d="M0 797 Q270 758 540 797 V960 H0Z" fill="url(#v2nightfloor)"/>'
      '<path d="M0 850 Q270 822 540 850 M0 910 Q270 878 540 910" fill="none" stroke="#a8b5a8" stroke-width="2" opacity=".13"/>'
      '<path d="M40 806 L0 960 M174 791 L145 960 M432 791 L481 960" fill="none" stroke="#a8b5a8" stroke-width="2" opacity=".09"/>')


def lit_window(t,small=False):
    # This is a real, independently animated cutaway behind the window frame.
    a=['<rect x="306" y="177" width="211" height="276" rx="4" fill="#142b37" stroke="#9aa9a0" stroke-width="7"/>',
       '<rect x="319" y="190" width="185" height="250" fill="url(#v2window)"/>',
       '<path d="M319 392 H504 V440 H319Z" fill="#9b786b"/>',
       '<path d="M321 228 L504 216 M321 384 H504" stroke="#f9e4bf" stroke-width="2" opacity=".22"/>',
       '<g clip-path="url(#v2winclip)">']
    a.append(person(363,433,.32,'man',view=.85,t=t,pose='argue',gesture=.55+.10*math.sin(t*4),anger=.9,talk=speech_amp('man_window',t)))
    a.append(person(458,433,.31,'woman',view=.72,facing=-1,t=t,pose='defend',gesture=.32+.12*math.sin(t*2),worry=.75,talk=speech_amp('woman_window',t)))
    a.extend(['</g>','<path d="M411 190 V440 M319 306 H504" stroke="#8f8d7c" stroke-width="4" opacity=".55"/>',
       '<path d="M326 196 H362 L326 237Z" fill="#fff9da" opacity=".25"/>',
       '<path d="M306 451 H518 L527 462 H296Z" fill="#7e9089"/>'])
    return ''.join(a)


def wall_lamp(x,y):
    return (f'<circle cx="{x}" cy="{y+14}" r="128" fill="url(#v2lamp)"/>'
      f'<path d="M{x-25} {y-20} H{x+25} L{x+19} {y+8} H{x-19}Z" fill="#f1dbae" stroke="#66766f" stroke-width="3"/>'
      f'<path d="M{x-16} {y+8} H{x+16}" stroke="#fdf0ca" stroke-width="3"/>')


def hallway_base():
    return ('<rect width="540" height="960" fill="url(#v2hall)"/>'
      '<path d="M0 0 H540 V225 L0 291Z" fill="#d0d5be" opacity=".09"/>'
      '<path d="M0 294 L540 230 M0 538 L540 494" stroke="#d8ded0" stroke-width="3" opacity=".13"/>'
      '<path d="M0 716 H540 V805 H0Z" fill="#415a60" opacity=".32"/>'
      '<path d="M0 715 H540 M0 789 H540" fill="none" stroke="#c5d0bf" stroke-width="4" opacity=".23"/>'
      '<path d="M0 806 H540 V960 H0Z" fill="url(#v2hallfloor)"/>'
      '<path d="M0 859 H540 M0 926 H540 M110 806 L42 960 M246 806 L220 960 M388 806 L445 960" fill="none" stroke="#d0d5c4" stroke-width="2" opacity=".18"/>'
      '<path d="M15 405 l18 -5 m-10 11 l12 -2 M475 609 l31 -2 M71 678 l21 -4" stroke="#344d53" stroke-width="2" opacity=".22"/>')


def door_leaf(x,y,width,height=610,damage=0):
    """A door turning around its hinge; damage stays on the leaf."""
    a=[f'<g transform="translate({n(x)} {n(y)}) scale({n(width/190)} 1)">',
       f'<path d="M0 0 H190 V{height} H0Z" fill="url(#v2wood)" stroke="#403c3a" stroke-width="4"/>',
       f'<path d="M13 20 H177 V{height-18} H13Z" fill="none" stroke="#c49a7a" stroke-width="2" opacity=".28"/>',
       '<path d="M25 77 H161 V230 H25Z M25 289 H161 V477 H25Z" fill="none" stroke="#c49a7a" stroke-width="3" opacity=".24"/>',
       '<path d="M31 83 H154 M31 295 H154" stroke="#3f3535" stroke-width="2" opacity=".4"/>',
       '<rect x="20" y="285" width="6" height="28" rx="3" fill="#d9be87"/><circle cx="23" cy="299" r="5" fill="#e9d2a0"/>']
    if damage>0:
        a.append(f'<g opacity="{n(damage)}"><path d="M24 389 l20 -15 17 12 20 -13 14 21 22 6 -12 20 11 17 -23 5 -10 22 -21 -10 -17 11 -7 -22 -21 -7 12 -16 -12 -13Z" fill="#273942" stroke="#e1b68d" stroke-width="4" stroke-linejoin="round"/>')
        a.append('<path d="M33 392 l-19 -23 -9 -26 M91 398 l31 -22 13 -31 M36 438 l-23 27 -7 31 M91 444 l32 18 11 29 M60 382 l-4 -40" fill="none" stroke="#e4b98c" stroke-width="3"/></g>')
    a.append('</g>')
    return ''.join(a)


def exit_scene(t):
    # A side-on exit from the protagonist's apartment, then a cut to the swing.
    walk=pulse(.40,.75,3.65,4.25,t)
    progress=smooth(.40,4.0,t)
    x=mix(161,341,progress)
    door_open=pulse(.05,.9,2.9,3.9,t)
    leaf_width=190*(1-.68*door_open)
    a=[hallway_base(),wall_lamp(445,198),
       '<path d="M64 199 H290 V811 H64Z" fill="#263f48" stroke="#91a49b" stroke-width="7"/>',
       '<path d="M77 210 H278 V802 H77Z" fill="#be9470"/>',
       '<path d="M77 210 H278 V802 H77Z" fill="url(#v2lit)"/>',
       '<path d="M77 651 H278 V802 H77Z" fill="#987763"/>',
       door_leaf(278-leaf_width,210,leaf_width,592),
       '<path d="M64 199 H290 V811 H64Z" fill="none" stroke="#90a29a" stroke-width="7"/>',
       '<rect x="27" y="535" width="25" height="40" rx="4" fill="#b2bcb0" opacity=".6"/><circle cx="40" cy="555" r="3" fill="#6b7c78"/>',
       '<path d="M74 810 H286 L305 826 H57Z" fill="#b9bcb0" opacity=".7"/>']
    a.append(person(x,820,.70,'hero',view=.88,facing=1,t=t,walk=walk,phase=(t-.25)*7.6,lean=2*walk,head_tilt=-2+1.2*math.sin(t*1.4)))
    return ''.join(a)


def swing_back(cx=147,top=288,seat=742,width=86):
    l=cx-width/2;r=cx+width/2
    return (f'<path d="M{n(cx-94)} {n(top)} H{n(cx+100)} M{n(cx-87)} {n(top)} L{n(cx-135)} 884 M{n(cx+92)} {n(top)} L{n(cx+148)} 884" fill="none" stroke="#526b6c" stroke-width="9" stroke-linecap="round"/>'
      f'<path d="M{n(cx-94)} {n(top-3)} H{n(cx+100)}" stroke="#b0beb0" stroke-width="2" opacity=".35"/>'
      f'<path d="M{n(l)} {n(top)} V{n(seat)} M{n(r)} {n(top)} V{n(seat)}" fill="none" stroke="#c0c8bd" stroke-width="3.5"/>')


def swing_seat(cx=147,seat=742,width=86):
    return (f'<path d="M{n(cx-width/2-9)} {n(seat)} Q{n(cx)} {n(seat+7)} {n(cx+width/2+9)} {n(seat)} L{n(cx+width/2+7)} {n(seat+10)} Q{n(cx)} {n(seat+16)} {n(cx-width/2-7)} {n(seat+10)}Z" fill="#96745c" stroke="#3c5558" stroke-width="3"/>')


def swing_scene(t):
    sit=smooth(4.44,5.33,t)
    amplitude=smooth(5.1,6.1,t)*4.3
    angle=amplitude*math.sin((t-5.1)*2.0)
    a=[sky(t),facade(),courtyard_floor(),'<circle cx="409" cy="324" r="180" fill="url(#v2lamp)" opacity=".22"/>',lit_window(t)]
    # The chains, seat and character rotate together about their crossbar.
    a.append(f'<g transform="rotate({n(angle)} 147 288)">')
    a.append(swing_back())
    a.append(swing_seat())
    a.append(person(147,mix(880,930,sit),.59,'hero',view=.63,facing=1,t=t,sit=sit,phase=(t-5)*2.1,lean=-1.5+angle*.4,head_tilt=-3))
    # Foreground chain catches the hand rather than floating beside it.
    a.append('<path d="M190 288 V625" fill="none" stroke="#c1ccc1" stroke-width="2.5" opacity=".8"/>')
    a.append('</g>')
    return ''.join(a)


def room_background(memory=False):
    a=['<rect width="540" height="960" fill="url(#v2warm)"/>',
       '<path d="M0 0 H540 V190 L0 252Z" fill="#f8e6ca" opacity=".12"/>',
       '<path d="M0 698 H540 V960 H0Z" fill="url(#v2roomfloor)"/>',
       '<path d="M0 695 H540" stroke="#e7c5a3" stroke-width="7" opacity=".62"/>',
       '<path d="M0 795 H540 M0 888 H540 M135 698 L70 960 M416 698 L485 960" fill="none" stroke="#eed2b3" stroke-width="2" opacity=".16"/>',
       '<rect x="35" y="221" width="131" height="176" fill="#8b716b" stroke="#6f5f5c" stroke-width="6"/>',
       '<rect x="44" y="230" width="113" height="158" fill="#6d8f8b"/><path d="M100 230 V388 M44 306 H157" stroke="#dac4a4" stroke-width="5"/>',
       '<path d="M35 215 Q44 286 37 400 H55 Q60 280 50 215 M152 215 Q143 280 146 400 H166 Q162 280 170 215" fill="#e6c8a4" opacity=".68"/>',
       '<rect x="386" y="235" width="109" height="88" rx="2" fill="#6a5c5a" stroke="#e4caa8" stroke-width="5"/>',
       '<path d="M396 309 Q418 277 439 295 Q456 268 485 300 V313 H396Z" fill="#b5b9a1"/>',
       '<path d="M118 535 Q120 494 150 493 H385 Q416 495 418 535 V660 H118Z" fill="#a68174" stroke="#795f5d" stroke-width="4"/>',
       '<path d="M126 572 H410 M215 500 V569 M309 500 V569 M133 648 H403" stroke="#e2bea2" stroke-width="3" opacity=".22"/>',
       '<circle cx="277" cy="227" r="148" fill="url(#v2lamp)" opacity=".48"/>',
       '<path d="M251 151 H303 L295 183 H258Z" fill="#f1d5ad" stroke="#8e7970" stroke-width="3"/>']
    if memory:
        a.append('<rect width="540" height="960" fill="#f0ce99" opacity=".07"/>')
    return ''.join(a)


def confrontation_scene(t):
    attack=pulse(11.77,12.14,12.24,12.72,t)
    recoil=pulse(12.17,12.48,12.90,13.50,t)
    wary=smooth(10.67,11.18,t)
    shake=(1-smooth(12.2,12.6,t))*smooth(12.1,12.2,t)
    # A stationary painted bleed behind the shaking scene prevents black
    # edges from appearing during the impact.
    a=[room_background(),f'<g transform="translate({n(shake*3*math.sin(t*47))} {n(shake*2*math.cos(t*37))})">',room_background()]
    a.append(person(362+20*recoil,800,.73,'woman',view=.80,facing=-1,t=t,pose='defend',gesture=.30+.55*wary,worry=.90,lean=7*recoil,head_tilt=4+6*recoil,talk=speech_amp('woman_window',t)))
    # Paint the attacking hand in front of the woman's face on contact rather
    # than hiding it behind her, so the action is unmistakable without gore.
    a.append(person(190+19*attack,800,.76,'man',view=.90,facing=1,t=t,pose='strike' if t>=11.76 else 'argue',gesture=attack if t>=11.76 else (.50+.12*math.sin(t*4)),anger=.96,lean=5*attack,head_tilt=-2,talk=speech_amp('man_window',t)))
    if 12.12<t<12.42:
        flash=1-abs(t-12.27)/.15
        a.append(f'<g opacity="{n(clamp(flash))}" stroke="#fff2d5" stroke-width="3.5" stroke-linecap="round"><path d="M340 335 l-15 -6 M342 319 l-8 -14 M341 350 l-14 7"/></g>')
    a.append('</g>')
    return ''.join(a)


def reaction_scene(t):
    stand=smooth(13.65,14.55,t)
    think=pulse(18.75,19.35,20.1,20.55,t)
    turn=smooth(14.55,15.15,t)
    second=smooth(18.15,19.05,t)
    view=mix(.62,.96,turn);view=mix(view,.30,second)
    angry=pulse(16.55,17.35,18.25,19.20,t)
    x=mix(245,171,stand);ground=mix(930,865,stand)
    a=[sky(t),facade(),courtyard_floor(),lit_window(t),
       '<path d="M105 221 H382 M113 221 L52 872 M374 221 L436 872" fill="none" stroke="#526b6b" stroke-width="10" stroke-linecap="round"/>',
       '<path d="M184 221 V678 M306 221 V678" fill="none" stroke="#b8c8bf" stroke-width="3"/>',
       swing_seat(245,679,122)]
    # A hesitant half-open palm and a lowered head are more readable and
    # anatomically credible here than twisting the forearm under the chin.
    a.append(person(x,ground,.78,'hero',view=view,t=t,sit=1-stand,phase=t*2.0,pose='question' if think>.005 else ('angry' if angry>.15 else 'idle'),gesture=.65*think,anger=angry*.85,worry=.25+.45*second,lean=-2*stand-2*think,head_tilt=-2-5*think))
    return ''.join(a)


def memory_scene(t):
    arguing=1-smooth(26.4,28.1,t)
    enter=smooth(24.55,26.05,t)
    walk=pulse(24.55,24.85,25.7,26.05,t)
    mediate=pulse(25.65,26.25,28.65,29.7,t)
    peace=smooth(28.45,29.25,t)
    momx=mix(142,170,peace);dadx=mix(370,346,peace);unclex=mix(610,260,enter)
    a=[room_background(True)]
    # Uncle crosses behind them and holds out both hands; parents stop gesturing.
    a.append(person(unclex,769,.53,'uncle',view=.38,facing=-1,t=t,walk=walk,phase=t*7.6,pose='mediate',gesture=mediate,head_tilt=-2))
    mg=arguing*(.69+.20*math.sin(t*3.5))+.87*peace
    dg=arguing*(.69+.20*math.sin(t*3.5+1.4))+.87*peace
    a.append(person(momx,769,.55,'mom',view=.78,facing=1,t=t,pose='question',gesture=mg,anger=.30*arguing,worry=.50*arguing,lean=2*arguing,talk=arguing*max(0,math.sin(t*6))*.45))
    a.append(person(dadx,769,.56,'dad',view=.78,facing=-1,t=t,pose='question',gesture=dg,anger=.70*arguing,lean=3*arguing,talk=arguing*max(0,math.sin(t*6+2))*.45))
    a.append(person(63,861,.40,'child',view=.65,facing=1,t=t,worry=.60*arguing,head_tilt=-4,lean=-2*arguing))
    if peace>.01:
        # Their two reaching hands meet in front of the uncle.
        a.append(f'<g opacity="{n(peace)}"><path d="M250 547 q6 -5 12 -1 l5 5 q-5 7 -12 6 l-7 -4Z" fill="url(#v2skin)" stroke="#8d655e" stroke-width="1.5"/></g>')
    a.append('<rect x="166" y="105" width="208" height="32" rx="16" fill="#413b3a" opacity=".65"/>')
    a.append(text(270,127,'ВОСПОМИНАНИЕ',13,700,'#f8e5cf'))
    return ''.join(a)


def stair_floor(x):
    # Matches the visible tread geometry below: each tread is 70 by 35.
    return 920-35*math.floor((x+50)/70)


def stair_scene(t):
    progress=smooth(30.55,35.55,t);x=mix(103,435,progress)
    walk=pulse(30.45,30.75,35.30,35.85,t)
    # The pelvis moves smoothly uphill while feet are solved against actual
    # tread heights individually; this prevents the previous floating feet.
    y=923-.50*x
    a=['<rect width="540" height="960" fill="url(#v2hall)"/>',
       '<path d="M0 0 H540 V390 L0 650Z" fill="#d6dfc8" opacity=".10"/>',wall_lamp(116,172)]
    # Treads and risers are actual paths, not an image of stairs.
    d='M-50 930 '
    for i in range(10):
        yy=920-i*35;xx=-50+i*70
        if i==0:d=f'M{xx} {yy} '
        d+=f'H{xx+70} V{yy-35} '
    d+='L650 960 H-50Z'
    a.append(f'<path d="{d}" fill="#637b79" stroke="#39575a" stroke-width="4"/>')
    for i in range(9):
        xx=-50+i*70;yy=920-i*35
        a.append(f'<path d="M{xx} {yy} H{xx+70}" stroke="#c3cfbd" stroke-width="5" opacity=".58"/>')
    a.append('<path d="M-30 637 L570 330" stroke="#324e51" stroke-width="9" stroke-linecap="round"/>')
    for xx in [35,150,265,380,495]:
        yy=637-(xx+30)*.512
        a.append(f'<path d="M{xx} {n(yy)} V{n(stair_floor(xx)-26)}" fill="none" stroke="#405d5c" stroke-width="6"/>')
    a.append(person(x,y,.66,'hero',view=.96,facing=1,t=t,walk=walk,phase=(t-30.5)*8.2,lean=4*walk,head_tilt=-2,foot_floor=stair_floor))
    return ''.join(a)


def hallway_scene(t):
    open_door=pulse(38.15,38.85,47.42,47.78,t)
    damage=smooth(53.50,53.62,t)
    forced=smooth(53.63,54.10,t)
    opened=max(open_door,forced)
    width=190*(1-.78*opened)
    enter=smooth(54.20,55.75,t)
    approach=smooth(36.35,37.03,t)
    retreat=smooth(52.3,53.04,t)
    jolt=pulse(47.58,47.76,47.86,48.25,t)
    hx=mix(91,190,approach)-48*retreat-13*jolt
    hx=mix(hx,386,enter)
    hs=mix(.68,.57,enter)
    # Three deliberately spaced taps, each at the sound cue.
    knock_window=pulse(36.95,37.12,37.92,38.22,t)
    taps=(.87+.13*math.cos((t-37.20)*2*math.pi/.32))*knock_window
    question=pulse(40.30,40.75,43.40,43.94,t)
    question*=.86+.10*math.sin((t-40.3)*2.4)
    warn=pulse(44.02,44.60,46.80,47.31,t)
    angry=smooth(47.7,49.0,t)
    kick=pulse(53.10,53.52,53.70,54.16,t)
    step=(pulse(36.35,36.55,36.83,37.05,t)+pulse(52.30,52.5,52.9,53.06,t)+pulse(54.10,54.35,55.40,55.75,t))
    a=[hallway_base(),wall_lamp(110,160),
       '<path d="M305 185 H518 V812 H305Z" fill="#2b4147" stroke="#9cac9f" stroke-width="7"/>',
       '<path d="M319 198 H505 V806 H319Z" fill="#ad8b70"/>',
       '<path d="M319 663 H505 V806 H319Z" fill="#806b60"/>',
       '<path d="M319 198 H505 V806 H319Z" fill="url(#v2lit)" opacity=".8"/>']
    if 38.15<t<47.80:
        # The extended hand is allowed past the jamb; clipping the actor to
        # the opening made the hand appear amputated during the warning.
        a.append(person(414,804,.66,'man',view=.82,facing=-1,t=t,pose='warn',gesture=warn,anger=.86,head_tilt=-2,talk=speech_amp('man',t)))
    # Door is hinged on the right. The neighbour is actually hidden as it slams.
    a.append(door_leaf(505-width,198,width,608,damage))
    # The frame was painted behind the actor already. Repainting the left
    # jamb here would cut the neighbour's gesturing wrist in half.
    a.append('<path d="M295 812 H527 L534 825 H286Z" fill="#a5b6a9"/>')
    if damage>0:
        u=clamp((t-53.55)/1.35)
        for i in range(10):
            xx=353+(i-4.5)*16*u
            yy=590-(42+i*8)*math.sin(math.pi*u)+205*u
            angle=(i-4)*15+u*(110+i*19)
            a.append(f'<path d="M-11 -3 L12 -2 L5 4 L-9 2Z" transform="translate({n(xx)} {n(yy)}) rotate({n(angle)})" fill="#d3aa83" stroke="#6b564b" stroke-width="1.5" opacity="{n(damage)}"/>')
    if kick>.01:pose='angry';gesture=0
    elif taps>.01:pose='knock';gesture=taps
    elif question>.01:pose='question';gesture=question
    else:pose='angry' if angry>.25 else 'idle';gesture=0
    # After the slam he turns toward us, weighs the decision, then turns back
    # towards the door before the kick. The motion is a drawn 2D head/body morph.
    reaction_turn=pulse(48.05,49.35,51.2,52.75,t)
    a.append(person(hx,812,hs,'hero',view=.95-.55*reaction_turn,facing=1,t=t,walk=min(1,step),phase=t*8.0,pose=pose,gesture=gesture,anger=angry*.9,worry=.25*(1-angry),lean=-9*kick-4*jolt+2*step,head_tilt=-2-3*angry,talk=speech_amp('hero',t),kick=kick))
    # Gentle motivated camera push during the conversation; it backs out for
    # the action, keeping the protagonist in frame from hair to shoes.
    zoom=1+.045*pulse(38.0,41.0,51.2,53.0,t)
    return f'<g transform="translate(270 560) scale({n(zoom)}) translate(-270 -560)">'+''.join(a)+'</g>'


def title_scene(t):
    a=['<rect width="540" height="960" fill="#0b1725"/>',
       '<circle cx="270" cy="385" r="230" fill="url(#v2lit)" opacity=".36"/>',
       '<path d="M115 517 H425" stroke="#bba478" stroke-width="1" opacity=".5"/>']
    opacity=smooth(56.0,56.38,t)
    a.append(f'<g opacity="{n(opacity)}">')
    a.append(text(270,368,'ПРОДОЛЖЕНИЕ СЕРИАЛА',15,700,'#c1ceca'))
    a.append(text(270,435,'«ВМЕШАТЬСЯ»',34,700,'#f4f3e9'))
    a.append(text(270,485,'СЛЕДУЕТ…',23,700,'#e8c47d'))
    a.append(text(270,803,'ЗВУК: OCULUS AUDIO PACK 01 — OCULUS VR, LLC (ИЗМЕНЕНО)',9,400,'#9eafb0'))
    a.append(text(270,820,'developers.meta.com/vr/downloads/package/oculus-audio-pack-1/',8,400,'#9eafb0'))
    a.append(text(270,836,'CC BY 4.0 · creativecommons.org/licenses/by/4.0/',9,400,'#9eafb0'))
    a.append('</g>')
    return ''.join(a)


# The window/interior/reaction cuts carry sound across the edit for continuity.
# A brief warm flash signals memory, and two short dips change location without
# the distracting double-exposed bodies caused by a conventional dissolve.
# The title is deliberately a hard cut.
SCENES=[(0.0,exit_scene),(4.42,swing_scene),(9.35,confrontation_scene),
        (13.55,reaction_scene),(20.65,memory_scene),(30.30,stair_scene),
        (36.40,hallway_scene),(56.0,title_scene)]
DIPS={4.42:(.24,'#152a38'),20.65:(.44,'#efd1ad'),30.30:(.34,'#243a45')}

CAPTIONS=[
 (.18,2.27,['В ту ночь я вышел из квартиры.']),
 (2.42,4.43,['Мне хотелось просто побыть одному.']),
 (4.82,6.57,['Я сел на качели во дворе.']),
 (6.96,8.02,['Замолчи!']),
 (8.20,9.60,['Я сказал: замолчи!']),
 (9.74,10.85,['Ты меня слышишь?!']),
 (10.95,12.42,['Не трогай меня, пожалуйста!']),
 (12.42,14.10,['Прекрати! Помогите!']),
 (14.25,16.55,['Из окна напротив доносились крики.']),
 (16.75,18.80,['Я разозлился, но остановился.']),
 (19.02,20.60,['Может, это не моё дело?']),
 (20.72,22.45,['И тут я вспомнил детство.']),
 (22.75,24.55,['Мои родители тоже ругались,']),
 (24.80,26.78,['пока однажды не пришёл дядя.']),
 (27.02,28.82,['Он спокойно поговорил с ними,']),
 (29.02,30.25,['и они помирились.']),
 (32.90,34.60,['Я не мог оставаться в стороне.']),
 (34.88,36.99,['Я поднялся наверх и постучал.']),
 (39.05,39.98,['Чё надо?']),
 (40.43,41.42,['Здравствуйте.']),
 (41.48,42.46,['Что за крики?']),
 (42.54,43.85,['Могу ли я вмешаться?']),
 (44.18,45.20,['Слышишь, парень,']),
 (45.67,47.24,['уходи отсюда по-доброму.']),
 (48.10,50.25,['Он захлопнул дверь','у меня перед носом.']),
 (50.65,52.62,['Я больше не мог стоять в стороне.']),
]


def captions(t):
    for start,end,lines in CAPTIONS:
        if start<=t<end:
            op=min(smooth(start,start+.08,t),1-smooth(end-.1,end,t))
            h=38 if len(lines)==1 else 62
            y=79 if len(lines)==1 else 72
            width=496
            s=[f'<g opacity="{n(op)}"><rect x="22" y="{y-26}" width="{width}" height="{h}" rx="9" fill="#0a1822" opacity=".82"/>']
            for i,line in enumerate(lines):s.append(text(270,y+i*23,line,17,700,'#f7f7ef'))
            return ''.join(s)+'</g>'
    return ''


def frame_svg(t):
    t=max(0,min(DURATION-1/FPS,t))
    scene=SCENES[0][1]
    for start,fn in SCENES:
        if t>=start:scene=fn
    body=scene(t)
    for cut,(length,color) in DIPS.items():
        if cut-length/2<=t<cut+length/2:
            amount=smooth(cut-length/2,cut,t) if t<cut else 1-smooth(cut,cut+length/2,t)
            body+=f'<rect width="540" height="960" fill="{color}" opacity="{n(.92*amount)}"/>'
            break
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">'
      +rig.DEFS+DEFS+body+'<rect width="540" height="960" fill="url(#v2vignette)" pointer-events="none"/>'
      +captions(t)+'</svg>')


def frame_png(t,w=RENDER_W,h=RENDER_H):
    return resvg_py.svg_to_bytes(svg_string=frame_svg(t),width=w,height=h,skip_system_fonts=True,font_files=FONT_FILES)


def audio_mix():
    sr=44100;count=DURATION*sr
    tt=np.arange(count,dtype=np.float32)/sr
    track=np.zeros((count,2),dtype=np.float32)
    def add(start,signal,vol=1.,pan=0.):
        start_i=int(start*sr)
        if start_i<0:signal=signal[-start_i:];start_i=0
        length=min(len(signal),count-start_i)
        if length<=0:return
        s=signal[:length]
        if s.ndim==1:
            track[start_i:start_i+length,0]+=s*vol*(1-.35*pan)
            track[start_i:start_i+length,1]+=s*vol*(1+.35*pan)
        else:
            track[start_i:start_i+length,0]+=s[:,0]*vol*(1-.35*pan)
            track[start_i:start_i+length,1]+=s[:,1]*vol*(1+.35*pan)
    # Natural ambient layers fade with the changing location.
    night=old.decode_ogg(SOUNDS/'AMBForst_Night_LOOP_01.ogg',sr)
    city=old.decode_ogg(SOUNDS/'AMBUrbn_CityAmerican_LOOP_01.ogg',sr)
    ambient_duration=int(20.65*sr)
    env=np.ones(ambient_duration,dtype=np.float32)
    ts=np.arange(ambient_duration,dtype=np.float32)/sr
    env*=np.clip((ts-3.9)/.8,0,1)*np.clip((20.65-ts)/.7,0,1)
    env*=np.where((ts>=9.35)&(ts<13.55),.18,1.)
    for sound,gain in [(night,.23),(city,.035)]:
        if len(sound)<ambient_duration:sound=np.tile(sound,(math.ceil(ambient_duration/len(sound)),1))
        add(0,sound[:ambient_duration]*env[:,None],gain)
    rng=np.random.default_rng(8271)
    noise=rng.normal(0,1,count).astype(np.float32)
    cs=np.cumsum(np.pad(noise,(72,0)),dtype=np.float64)
    air=((cs[72:]-cs[:-72])/72).astype(np.float32)
    add(0,air*(.005+np.where((tt>=4.4)&(tt<20.6),.014,.004)))
    # Quiet original underscoring: a few evolving minor chords, never over dialogue.
    chords=[(0,146.83,174.61,220.),(6.4,130.81,164.81,196.),(13.1,146.83,174.61,220.),
            (20.5,130.81,164.81,196.),(26.0,174.61,220.,261.63),(30.3,146.83,174.61,220.),
            (36.0,123.47,146.83,185.0),(42.0,130.81,155.56,196.),(48.0,110.,130.81,164.81),(53.0,98.,116.54,146.83)]
    for start,f1,f2,f3 in chords:
        dur=min(7.,56-start);u=np.arange(int(sr*dur),dtype=np.float32)/sr
        env=np.minimum(1,u/.9)*np.minimum(1,(dur-u)/1.0)
        pad=(np.sin(2*np.pi*f1*u)+.50*np.sin(2*np.pi*f2*u)+.36*np.sin(2*np.pi*f3*u)+.12*np.sin(2*np.pi*f1*2*u))*env
        add(start,pad,.011)
    for path,start,role in VOICES:
        signal,sr0=voice(path)
        if sr0!=sr:raise ValueError(f'expected {sr} Hz: {path}')
        rms=float(np.sqrt(np.mean(signal*signal))) or 1
        gain=min(.125/rms,.82/(float(np.max(np.abs(signal)))+1e-7))
        signal=signal*gain
        if role=='man_window':
            # Across the cut, the same shout comes through the window, then
            # becomes direct sound inside the apartment; no jump in timing.
            u=start+np.arange(len(signal),dtype=np.float32)/sr
            z=np.clip((u-9.20)/.30,0,1)
            low=np.convolve(signal,np.ones(7,dtype=np.float32)/7,mode='same')
            signal=(1-z)*low*.67+z*signal*.96
        elif role=='woman_window':
            u=start+np.arange(len(signal),dtype=np.float32)/sr
            z=np.clip((u-13.55)/.30,0,1)
            low=np.convolve(signal,np.ones(7,dtype=np.float32)/7,mode='same')
            signal=(1-z)*signal*.96+z*low*.70
        add(start,signal,1.,.14 if role.endswith('window') else 0.)
    fs0=old.decode_ogg(FOLEY/'footstep_concrete_000.ogg',sr)
    fs1=old.decode_ogg(FOLEY/'footstep_concrete_003.ogg',sr)
    wood=old.decode_ogg(SOUNDS/'footstep_wood_002.ogg',sr)
    creak=old.decode_ogg(SOUNDS/'creak1.ogg',sr)
    opening=old.decode_ogg(FOLEY/'doorOpen_1.ogg',sr)
    close=old.decode_ogg(SOUNDS/'doorClose_4.ogg',sr)
    knock=old.decode_ogg(SOUNDS/'impactWood_light_001.ogg',sr)
    heavy=old.decode_ogg(SOUNDS/'impactWood_heavy_002.ogg',sr)
    plank=old.decode_ogg(SOUNDS/'impactPlank_medium_001.ogg',sr)
    punch=old.decode_ogg(SOUNDS/'impactPunch_medium_001.ogg',sr)
    latch=old.decode_ogg(FOLEY/'metalLatch.ogg',sr)
    add(.2,opening,.12,-.15)
    for i in range(1,10):
        when=.25+i*math.pi/7.6
        if when<3.95:add(when,wood,.14,-.2 if i%2 else .2)
    add(3.65,close,.16,-.25)
    for when in (5.7,7.2,8.7):add(when,creak,.12,-.3)
    add(12.17,punch,.13,.23)
    for i in range(1,14):
        when=30.5+i*math.pi/8.2
        if when>=35.6:break
        add(when,fs0 if i%2 else fs1,.16,-.22 if i%2 else .22)
        add(when+.09,fs1,.025,.2)
    add(36.65,fs0,.12,-.2);add(37.01,fs1,.12,.1)
    for when in (37.20,37.52,37.84):add(when,knock,.28,.3)
    add(38.35,opening,.19,.28)
    add(47.70,close,.70,.25)
    add(52.58,fs0,.13,-.2);add(53.04,fs1,.11,-.1)
    add(53.52,heavy,.65,.30);add(53.57,plank,.53,.30);add(53.60,latch,.16,.25)
    add(54.64,wood,.13,.1);add(55.08,wood,.13,.2)
    fade=np.minimum(1,tt/.07)*np.minimum(1,(DURATION-tt)/.30)
    track*=fade[:,None]
    peak=float(np.max(np.abs(track)))
    if peak>.93:track*=.93/peak
    return (track*32767).astype('<i2'),sr


def write_wav(path):
    samples,sr=audio_mix()
    with wave.open(str(path),'wb') as f:
        f.setnchannels(2);f.setsampwidth(2);f.setframerate(sr);f.writeframes(samples.tobytes())


def render_frame_job(args):
    index,width,height=args
    return frame_png(index/FPS,width,height)


def render(output=OUTPUT,width=RENDER_W,height=RENDER_H,workers=2):
    output.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='vmeshat-v2-') as tmp:
        wav=Path(tmp)/'mix.wav';write_wav(wav)
        cmd=[imageio_ffmpeg.get_ffmpeg_exe(),'-hide_banner','-loglevel','error','-y',
             '-f','image2pipe','-vcodec','png','-framerate',str(FPS),'-i','-',
             '-i',str(wav),'-t',str(DURATION),'-vf',f'scale={OUTPUT_W}:{OUTPUT_H}:flags=lanczos',
             '-c:v','libx264','-preset','veryfast','-crf','20','-pix_fmt','yuv420p',
             '-c:a','aac','-b:a','192k','-movflags','+faststart',str(output)]
        proc=subprocess.Popen(cmd,stdin=subprocess.PIPE)
        try:
            # Bounded batches keep memory use predictable while two workers
            # rasterize independent keyframed vector frames in parallel.
            with ProcessPoolExecutor(max_workers=workers) as pool:
                total=FPS*DURATION
                for first in range(0,total,24):
                    jobs=((i,width,height) for i in range(first,min(first+24,total)))
                    for i,png in enumerate(pool.map(render_frame_job,jobs),first):
                        proc.stdin.write(png)
                        if i%(FPS*5)==0:print(f'{i//FPS:02d}s / {DURATION}s',flush=True)
        finally:
            proc.stdin.close()
        if proc.wait()!=0:raise RuntimeError('ffmpeg render failed')
    print(f'Complete: {output} ({output.stat().st_size/1_000_000:.1f} MB)',flush=True)


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--samples',action='store_true')
    ap.add_argument('--width',type=int,default=RENDER_W)
    ap.add_argument('--height',type=int,default=RENDER_H)
    ap.add_argument('--workers',type=int,default=2)
    ap.add_argument('--output',type=Path,default=OUTPUT)
    args=ap.parse_args()
    if args.workers<1:ap.error('--workers must be at least 1')
    if args.samples:
        folder=HERE/'previews';folder.mkdir(parents=True,exist_ok=True)
        for t in (0.7,2.1,4.8,6.8,8.4,9.8,11.4,12.16,12.4,13.9,15.5,17.4,19.5,21.5,24.8,26.6,29.4,31.8,34.1,36.8,37.2,39.4,41.8,45.6,47.7,50.2,53.0,53.53,53.8,54.5,55.5,57.5):
            p=folder/f'reworked_{t:.2f}.png';p.write_bytes(frame_png(t,540,960));print(p)
    else:render(args.output,args.width,args.height,args.workers)

if __name__=='__main__':main()
