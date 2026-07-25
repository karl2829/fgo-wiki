#!/usr/bin/env python3
"""FGO skill card - final rewrite. Arc stars, all square icons, clean separators."""
import io, os, math, requests
from PIL import Image, ImageDraw, ImageFont, ImageFilter

CARD_W = 700; PD = 24; BLK_GAP = 16; SEP_PCT = 0.85
FONT = "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc"
CLASS = os.path.expanduser("~/fgo-wiki/assets/classes")
CACHE = os.path.expanduser("~/fgo-wiki/cache/skill-icons")
os.makedirs(CACHE, exist_ok=True)

GOLD=(201,168,76); SILVER=(192,192,196); BRONZE=(205,127,50)
NAME_C="#1A1A2E"; DESC_C="#1A1A2E"; CD_C="#E04040"; VAL_C="#1A1A2E"
EMPTY_C="#BBBBBB"; NO_C="#999999"; SEP_C="#D8D4D0"; BD_C="#D0CCC8"
CARD_BG="#E8E4E0"

def font(sz):
    if os.path.exists(FONT):
        try: return ImageFont.truetype(FONT, sz, encoding="unic")
        except: pass
    return ImageFont.load_default()

def bbox(d,t,f):
    b=d.textbbox((0,0),t,font=f); return b[2]-b[0]

def wrap(t,f,mw,d):
    l,c=[],""
    for h in t:
        if bbox(d,c+h,f)>mw and c:
            l.append(c); c=h
        else: c+=h
    if c: l.append(c); return l

def dl(url,n):
    p=os.path.join(CACHE,n)
    if os.path.exists(p):
        try: return Image.open(p).convert("RGBA")
        except: pass
    try:
        r=requests.get(url,timeout=10,headers={"User-Agent":"fgo-wiki/1.0"})
        if r.status_code==200:
            with open(p,"wb") as f: f.write(r.content)
            return Image.open(p).convert("RGBA")
    except: pass
    return None

def sq(im,sz,r=0):
    im=im.resize(sz,Image.LANCZOS)
    if r>0:
        m=Image.new("L",sz,0)
        ImageDraw.Draw(m).rounded_rectangle([0,0,sz[0],sz[1]],r,fill=255)
        o=Image.new("RGBA",sz,(0,0,0,0))
        o.paste(im,(0,0),m); return o
    return im

# Test data
sd={"id":3035000,"name":"奥伯龙","class_id":13,"rarity":5,
    "face_url":"https://static.atlasacademy.io/CN/Faces/f_3035000.png","collection_no":316}
sk=[
 {"n":"夜之帷幕","r":"EX","cd":[7,6,5],"i":"",
  "e":[{"d":"己方全体的宝具威力提升(3回合)","v":[20,21,22,23,24,25,26,27,28,30]},
       {"d":"NP增加","v":[20]}]},
 {"n":"晨之云雀","r":"EX","cd":[8,7,6],"i":"",
  "e":[{"d":"己方单体的NP增加","v":[30,32,34,36,38,40,42,44,46,50]},
       {"d":"付与「回合结束时自身NP减少」的状态(1次)","v":[20]},
       {"d":"获得暴击星","v":[10,11,12,13,14,15,16,17,18,20]}]},
 {"n":"梦之终结","r":"EX","cd":[10,9,8],"i":"",
  "e":[{"d":"己方单体的Buster指令卡性能提升(1回合)","v":[30,32,34,36,38,40,42,44,46,50]},
       {"d":"付与宝具威力提升促进状态(1回合)","v":[50,55,60,65,70,75,80,85,90,100]},
       {"d":"付与「解除自身的强化状态」","v":None}]}]

def render(sid, out):
    rar=sd["rarity"]
    if rar>=4: ac=GOLD; st="★"*rar; rl="gold"
    elif rar==3: ac=SILVER; st="★"*rar; rl="silver"
    else: ac=BRONZE; st="★"*rar; rl="bronze"
    f11=font(11); f12=font(12); f14=font(14); f15=font(15); f16=font(16); f17=font(17)
    f18=font(18); f20=font(20); f24=font(24); f26=font(26)

    # Height calc
    h=130
    for s in sk:
        h+=54
        for e in s["e"]:
            n=max(len(wrap(e["d"],f17,CARD_W-PD*2-16,ImageDraw.Draw(Image.new("RGB",(1,1))))),1)
            h+=n*20+6+32+2
        h+=BLK_GAP
    h+=45

    # Card with shadow
    sh=Image.new("RGBA",(CARD_W+8,int(h)+8),(0,0,0,0))
    ImageDraw.Draw(sh).rounded_rectangle([4,4,CARD_W+3,int(h)+3],14,(0,0,0,25))
    sh=sh.filter(ImageFilter.GaussianBlur(5))
    img=Image.new("RGBA",(CARD_W+8,int(h)+8),CARD_BG)
    img.paste(sh,(0,0),sh)
    body=Image.new("RGBA",(CARD_W,int(h)),(255,255,255))
    bdr=ImageDraw.Draw(body)
    bdr.rounded_rectangle([0,0,CARD_W-1,int(h)-1],14,outline=BD_C,width=1)
    img.paste(body,(4,4),body)
    dr=ImageDraw.Draw(img)
    y=PD+8

    # ── Servant header ──
    av_sz=96
    av=dl(sd["face_url"],f"f{sid}.png")
    if av:
        av=sq(av,(av_sz,av_sz),6)
        ring=Image.new("RGBA",(av_sz+10,av_sz+10),(0,0,0,0))
        rdr=ImageDraw.Draw(ring)
        rdr.rounded_rectangle([3,3,av_sz+6,av_sz+6],8,outline=ac,width=3)
        img.paste(ring,(PD-5,y-5),ring)
        img.paste(av,(PD,y),av)

    # No.350 in top-right corner
    dr.text((CARD_W-PD-bbox(dr,f"No.{sd.get('collection_no','')}",f16)-6,PD+10),
            f"No.{sd.get('collection_no','')}",fill=NO_C,font=f16)

    # Name left of avatar
    nx=PD+av_sz+16
    dr.text((nx,y+20),sd["name"],fill=NAME_C,font=f26)

    # Class icon + arc: centered bottom of header
    ci_sz=56
    ci_x=(CARD_W-ci_sz)//2
    ci_y=y+86

    # Arc stars above class icon
    if rar>1:
        arc_r=64
        cx=ci_x+ci_sz//2
        cy=ci_y+ci_sz//2-4
        start_d=155; end_d=25
        for i in range(rar):
            fr=i/(rar-1) if rar>1 else 0.5
            deg=start_d+fr*(end_d-start_d)
            rad=math.radians(deg)
            sx=cx+arc_r*math.cos(rad)
            sy=cy-arc_r*math.sin(rad)
            dr.text((sx-8,sy-10),"★",fill=ac,font=f20)

    ip=os.path.join(CLASS,f"{sd['class_id']}_{rl}.png")
    if os.path.exists(ip):
        ci=Image.open(ip).convert("RGBA")
        ci=sq(ci,(ci_sz,ci_sz),8)
        img.paste(ci,(int(ci_x),int(ci_y)),ci)

    y+=170

    # ── Skills ──
    for si,s in enumerate(sk):
        bh=50
        for e in s["e"]:
            n=max(len(wrap(e["d"],f17,CARD_W-PD*2-16,dr)),1)
            bh+=n*20+6+32+2
        bh+=6

        iy=y+14

        # Skill icon: 52px SQUARE
        ic=dl(s["i"],f"sk{sid}_{si}.png")
        if ic:
            ic=sq(ic,(52,52),6)
            img.paste(ic,(PD+16,iy-4),ic)

        # Skill name 20px bold
        sm_x=PD+80
        dr.text((sm_x,iy+4),s["n"],fill=NAME_C,font=f20)
        xt=sm_x+bbox(dr,s["n"],f20)+4
        dr.text((xt,iy+6),s["r"],fill="#E04040",font=f16)

        # Cooldown RED
        cd=" → ".join(str(c) for c in sorted(set(s["cd"]),reverse=True))
        dr.text((CARD_W-PD-12-bbox(dr,cd,f16),iy+5),cd,fill=CD_C,font=f16)

        iy+=56

        for e in s["e"]:
            # Description: 17px dark, 12px gap from icon
            ls=wrap(e["d"],f17,CARD_W-PD*2-16,dr)
            n=max(len(ls),1)
            for li,l in enumerate(ls):
                dr.text((PD+18,iy+li*20),l,fill=DESC_C,font=f17)
            iy+=n*20+6

            va=e.get("v"); gy=iy
            if not va:
                bw=52; bgap=4; tw=bw*10+bgap*9; sx_=(CARD_W-tw)//2
                dr.rounded_rectangle([sx_,gy,sx_+tw,gy+28],6,fill="#FFFFFF",outline="#D8D0C8",width=1)
                dr.text((sx_+(tw-bbox(dr,"∅",f15))//2,gy+4),"∅",fill=EMPTY_C,font=f16)
                iy+=32
            elif len(va)<=1:
                bw=52; bgap=4; tw=bw*10+bgap*9; sx_=(CARD_W-tw)//2
                dr.rounded_rectangle([sx_,gy,sx_+tw,gy+28],6,fill="#FFFFFF",outline="#D8D0C8",width=1)
                vt=str(va[0])+"%" if va[0] and isinstance(va[0],(int,float)) and va[0]<1000 else str(va[0])
                dr.text((sx_+(tw-bbox(dr,vt,f16))//2,gy+4),vt,fill=VAL_C,font=f16)
                iy+=32
            else:
                bw=52; bgap=4; tw=bw*10+bgap*9; sx_=(CARD_W-tw)//2
                for ci in range(min(10,len(va))):
                    cx=sx_+ci*(bw+bgap)
                    vt=str(va[ci])+"%" if isinstance(va[ci],(int,float)) and va[ci]<1000 else str(va[ci])
                    dr.rounded_rectangle([cx,gy+1,cx+bw,gy+27],4,fill="#FFFFFF",outline="#D8D0C8",width=1)
                    dr.text((cx+(bw-bbox(dr,vt,f16))//2,gy+4),vt,fill=VAL_C,font=f16)
                    if ci in (0,5,9):
                        dr.text((cx+bw-13,gy-2),"★",fill=GOLD,font=f11)
                iy+=32

        y+=bh+BLK_GAP
        # Separator between blocks (85% width)
        if si<len(sk)-1:
            sep_w=int(CARD_W*SEP_PCT); sm=(CARD_W-sep_w)//2
            dr.line([(sm,y-BLK_GAP//2),(sm+sep_w,y-BLK_GAP//2)],fill=SEP_C,width=1)

    ft="Atlas Academy API · fgo-wiki 本地知识库"
    fw=bbox(dr,ft,f11)
    dr.text(((CARD_W-fw)//2,y+4),ft,fill=NO_C,font=f11)
    img.save(out,"PNG",dpi=(200,200))
    print(f"✅ {out} {CARD_W}x{int(h)} {os.path.getsize(out)//1024}KB")

if __name__=="__main__":
    import time
    t=time.time()
    render(204600,"/tmp/fgo_final_v4.png")
    print(f"{time.time()-t:.2f}s")
