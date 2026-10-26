"""Create the project's original illustrated film-poster collection as editable SVG.

No stock images, existing film artwork, external generation API or celebrity likenesses.
Run from the project root: python scripts/generate_original_art.py
"""

import math
import random
import sys
from pathlib import Path
from html import escape

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from app.original_catalog import CONCEPTS


def polygon(points, fill, **attrs):
    return (
        f'<polygon points="{points}" fill="{fill}" '
        + " ".join(f'{k.replace("_","-")}="{v}"' for k, v in attrs.items())
        + "/>"
    )


def circle(x, y, r, fill, extra=""):
    return f'<circle cx="{x}" cy="{y}" r="{r}" fill="{fill}" {extra}/>'


def line(x1, y1, x2, y2, color, width=2, extra=""):
    return f'<path d="M{x1} {y1}L{x2} {y2}" stroke="{color}" stroke-width="{width}" fill="none" {extra}/>'


def mountains(color="#10212e", base=870):
    return f'<path d="M-30 {base}L150 {base-300} 290 {base-120} 490 {base-470} 680 {base-180} 840 {base-370} 1040 {base}Z" fill="{color}"/>'


def person(x, y, scale=1, color="#08131d"):
    return (
        f'<g transform="translate({x} {y}) scale({scale})">'
        + circle(0, -34, 12, color)
        + f'<path d="M-13-18Q0-26 13-18L22 24H12L11 73H0L-3 32-8 73H-20L-17 22H-28Z" fill="{color}"/></g>'
    )


def tree(x, y, scale, color):
    return f'<g transform="translate({x} {y}) scale({scale})"><path d="M0-220-48-130H-27L-72-55H-42L-95 35H95L42-55H72L27-130H48Z" fill="{color}"/><path d="M-8 20H8V115H-8Z" fill="{color}"/></g>'


def skyline(rng, color="#0a1425", base=900, lit="#75dfda"):
    out = []
    for x in range(-20, 1050, 70):
        h = rng.randrange(150, 420)
        out.append(
            f'<rect x="{x}" y="{base-h}" width="62" height="{h}" fill="{color}"/>'
        )
        for wx in range(x + 10, x + 55, 15):
            for wy in range(base - h + 18, base - 10, 26):
                if rng.random() > 0.4:
                    out.append(
                        f'<rect x="{wx}" y="{wy}" width="5" height="9" fill="{lit}" opacity="{rng.uniform(.2,.65):.2f}"/>'
                    )
    return "".join(out)


def scene(theme, colors, rng):
    bg, accent, light = colors
    if theme == "orbit":
        return f"""<ellipse cx="650" cy="430" rx="460" ry="78" transform="rotate(-24 650 430)" fill="none" stroke="{accent}" stroke-width="3" opacity=".6"/>
        <circle cx="650" cy="410" r="252" fill="url(#planet)"/><circle cx="679" cy="388" r="236" fill="{bg}" opacity=".89"/>
        <path d="M414 455Q470 695 685 656" fill="none" stroke="{accent}" stroke-width="9" filter="url(#glow)"/>
        <ellipse cx="650" cy="430" rx="459" ry="78" transform="rotate(-24 650 430)" fill="none" stroke="{light}" stroke-width="1" opacity=".35"/>
        <path d="M0 1030Q280 720 1000 820V1200H0Z" fill="#07131c"/><path d="M0 1030Q280 720 1000 820" fill="none" stroke="{light}" stroke-width="3" opacity=".5"/>
        <g transform="translate(606 667) rotate(-12)"><rect x="-28" y="-18" width="56" height="76" rx="19" fill="#b9c5c8"/><rect x="-39" y="-9" width="15" height="68" rx="5" fill="#6a838d"/>
        <circle cy="-35" r="31" fill="#dce2db"/><path d="M-24-44Q0-64 24-44V-21Q0-7-24-21Z" fill="#233f4c"/>
        <path d="M-21 48-32 112H-13L0 69 12 112H30L22 47M-23-5-60 25M22-5 49 16" stroke="#b9c5c8" stroke-width="16" fill="none" stroke-linecap="round"/></g>
        <path d="M580 710C400 810 850 730 755 1075" fill="none" stroke="{accent}" stroke-width="3"/>
        <path d="M170 320l35-11 55 18-54 4Z" fill="{light}" opacity=".8"/>"""
    if theme == "city":
        return f"""{circle(630,360,190,accent,'opacity=".15" filter="url(#glow)"')}
        {skyline(rng,'#13213c',840,light)}{skyline(rng,'#0a152b',1060,accent)}
        <path d="M430 1200 530 550 585 1200" fill="{light}" opacity=".14"/>
        <path d="M480 1200 550 550 530 1200" fill="{accent}" opacity=".55"/>
        <rect x="553" y="250" width="13" height="512" fill="{light}" opacity=".9"/>
        <path d="M460 350 560 260 660 350" fill="none" stroke="{accent}" stroke-width="8"/>
        {person(560,828,1.3)}<path d="M509 794Q560 720 611 794Z" fill="{accent}"/>
        <g stroke="{light}" opacity=".22">{''.join(line(x,80,x-110,1040,light,1) for x in range(40,1100,70))}</g>"""
    if theme == "mountain":
        return f"""{circle(630,310,127,accent)}{mountains('#344e51',900)}{mountains('#183239',1070)}
        <path d="M490 430 453 523 490 498 523 523Z" fill="{light}" opacity=".65"/>
        <path d="M0 1070Q260 875 1000 950V1250H0Z" fill="#0b2229"/>
        <path d="M140 1060V650H300V1060Z" fill="#12232b"/><path d="M108 655 220 536 332 655Z" fill="{accent}"/>
        <path d="M175 664Q220 602 265 664V768H175Z" fill="#080f17"/>
        <path d="M220 639V723" stroke="{light}" stroke-width="5"/><path d="M196 723Q220 684 244 723Z" fill="{light}"/>
        {person(535,880,.9)}{tree(880,910,1.2,'#0b2028')}{tree(50,900,.9,'#0c2229')}"""
    if theme == "forest":
        trees = "".join(
            tree(x, 930, rng.uniform(0.7, 1.7), "#163a3a")
            for x in range(-20, 1100, 140)
        )
        return f"""{circle(550,350,168,light,'opacity=".65"')}{trees}
        <path d="M0 980Q500 840 1000 1030V1250H0Z" fill="#0a2527"/>
        <path d="M385 945Q330 845 425 804L590 851Q690 895 605 982Z" fill="{accent}"/>
        <path d="M410 815 416 686 493 763 556 692 584 852 499 904Z" fill="#e48635"/>
        <path d="M416 751 433 712 461 763M532 768 551 719 562 774" fill="#57382d"/>
        <path d="M420 824 499 871 579 824 527 899H475Z" fill="#f9e4b5"/>
        {circle(462,811,7,'#192d2c')}{circle(538,811,7,'#192d2c')}{polygon('486,856 514,856 500,869','#192d2c')}
        <path d="M604 937Q788 833 735 743Q750 909 641 991Z" fill="#e8983d"/><path d="M735 743Q750 825 712 865L686 817Z" fill="#f5dcb2"/>
        {''.join(circle(rng.randrange(80,930),rng.randrange(300,920),rng.randrange(2,5),light,'filter="url(#glow)"') for _ in range(22))}"""
    if theme == "midnight":
        return f"""{circle(635,290,100,light,'opacity=".75"')}{skyline(rng,'#151724',940,accent)}
        <path d="M0 1200 450 500H550L1000 1200Z" fill="#191824"/>
        <path d="M490 570 470 1100" stroke="{accent}" stroke-width="5" stroke-dasharray="45 32"/>
        <g transform="translate(520 705)"><rect x="-142" y="-130" width="284" height="320" rx="36" fill="#762d3e" stroke="{accent}" stroke-width="3"/>
        <rect x="-120" y="-90" width="240" height="130" rx="12" fill="#172938"/>
        <rect x="-85" y="-118" width="170" height="17" rx="4" fill="{accent}" opacity=".8"/>
        <path d="M0-90V40" stroke="#762d3e" stroke-width="9"/><rect x="-109" y="88" width="50" height="22" rx="5" fill="{light}"/>
        <rect x="59" y="88" width="50" height="22" rx="5" fill="{light}"/><path d="M-70 146H70" stroke="#271e2b" stroke-width="18"/>
        <path d="M-100 173V211M100 173V211" stroke="#0b111c" stroke-width="38"/></g>
        <path d="M411 804 120 1200H450L461 804M579 804 550 1200H940L629 804" fill="{light}" opacity=".09"/>"""
    if theme == "sea":
        waves = "".join(
            f'<path d="M0 {y}Q190 {y-30} 400 {y}T1000 {y}" fill="none" stroke="{light}" stroke-width="2" opacity=".25"/>'
            for y in range(720, 1160, 45)
        )
        return f"""{circle(690,310,136,accent,'opacity=".85"')}<rect y="660" width="1000" height="550" fill="#16495b"/>{waves}
        <path d="M545 850 695 690 820 850Z" fill="#102d3d"/><path d="M620 740 646 385H714L741 740Z" fill="#e5d3ad"/>
        <path d="M628 660H733M636 550H724M642 455H717" stroke="#c96e49" stroke-width="25"/>
        <rect x="632" y="345" width="96" height="53" rx="5" fill="#15394b"/><path d="M618 348 680 291 741 348Z" fill="#bf6b48"/>
        <path d="M639 369 160 520 90 240Z" fill="{accent}" opacity=".1"/><rect x="649" y="359" width="62" height="24" fill="{accent}"/>
        <g transform="translate(285 840) rotate(-13)"><rect width="170" height="108" rx="5" fill="#ecdbb5"/><path d="M0 0 85 63 170 0M0 108 62 53M170 108 108 53" stroke="#a78667" stroke-width="3" fill="none"/></g>"""
    if theme == "station":
        arches = "".join(
            f'<path d="M{x} 950V400Q500 {-100+x//3} {1000-x} 400V950" stroke="{accent}" stroke-width="9" fill="none" opacity=".3"/>'
            for x in (80, 180, 280)
        )
        return f"""{arches}<path d="M200 1200 470 660M800 1200 530 660" stroke="{light}" stroke-width="7"/>
        <g transform="translate(500 710)"><rect x="-145" y="-180" width="290" height="340" rx="75" fill="#23434b" stroke="{accent}" stroke-width="5"/>
        <rect x="-100" y="-117" width="200" height="100" rx="18" fill="#cbb788"/>
        <path d="M0-117V-17" stroke="#23434b" stroke-width="9"/>{circle(0,55,37,accent,'filter="url(#glow)"')}
        <path d="M-94 131H94" stroke="#101e29" stroke-width="27"/></g>
        {circle(500,256,53,'#1c3138',f'stroke="{accent}" stroke-width="3"')}
        <path d="M500 217V256L530 275" stroke="{light}" stroke-width="4" fill="none"/>
        {person(720,905,.9)}<path d="M70 900Q500 780 930 900V1100H70Z" fill="{light}" opacity=".06"/>"""
    if theme == "aurora":
        ribbons = "".join(
            f'<path d="M-100 {170+i*15}C250 {100+i*8} 350 {690-i*13} 1200 {230+i*8}" fill="none" stroke="{accent if i%2 else light}" stroke-width="{10+i*2}" opacity=".13" filter="url(#glow)"/>'
            for i in range(9)
        )
        return f"""{ribbons}{mountains('#183844',850)}<path d="M0 856H1000V1200H0Z" fill="#112e3b"/>
        {mountains('#0b2431',1100)}<path d="M230 1030 530 975 850 1030Z" fill="{accent}" opacity=".18"/>
        {person(560,832,.7)}{person(600,840,.66)}{tree(100,840,1.5,'#081e2b')}{tree(920,880,1.8,'#081e2b')}"""
    if theme == "bakery":
        stripes = "".join(
            f'<rect x="{198+i*60}" y="510" width="60" height="100" fill="{accent if i%2 else light}"/>'
            for i in range(10)
        )
        return f"""{circle(660,330,151,accent,'opacity=".3"')}<rect x="170" y="430" width="660" height="610" rx="12" fill="#c1876f"/>
        <rect x="206" y="623" width="240" height="325" fill="#613d3a"/><rect x="480" y="624" width="310" height="233" rx="8" fill="#f2c88f"/>
        <rect x="198" y="450" width="600" height="58" fill="#573637"/>{stripes}
        <path d="M535 773h200v35H535Z" fill="#b26c5c"/><path d="M555 704h160v69H555Z" fill="{light}"/><path d="M572 677h126v27H572Z" fill="{accent}"/>
        {''.join(circle(x,673,7,'#a94643') for x in (584,610,636,662,688))}
        <rect x="466" y="877" width="337" height="73" fill="#85544d"/>{person(340,868,1,'#4b3034')}
        <path d="M163 1032H839" stroke="{light}" stroke-width="8"/>"""
    if theme == "sunrise":
        grid = "".join(
            line(x, 1200, 500, 650, light, 1, 'opacity=".25"')
            for x in range(-500, 1600, 120)
        )
        return f"""{circle(580,450,214,accent)}{''.join(f'<rect x="300" y="{y}" width="560" height="{8+(y-450)//8}" fill="{bg}"/>' for y in range(455,665,32))}
        {skyline(rng,'#102535',970,light)}{grid}
        <path d="M0 898 240 790 500 855 820 720 1000 806" stroke="{accent}" stroke-width="8" fill="none"/>
        {person(690,830,1.05)}<path d="M625 755Q690 720 758 760" stroke="{light}" stroke-width="2" fill="none"/>
        {''.join(f'<path d="M{x} 260h40v40h-40Z" fill="none" stroke="{light}" opacity=".35"/>' for x in (100,230,810))}"""
    if theme == "house":
        return f"""{circle(690,310,150,light,'opacity=".6"')}<path d="M0 980Q500 825 1000 980V1200H0Z" fill="#111722"/>
        <path d="M230 900V495H770V900Z" fill="#303445"/><path d="M190 498 500 264 810 498Z" fill="#121c2c"/>
        <path d="M562 340V225H630V392Z" fill="#222b3c"/>
        <path d="M436 901V671Q500 593 564 671V901Z" fill="#111927"/>
        {''.join(f'<rect x="{x}" y="{y}" width="58" height="88" rx="24" fill="{accent}" opacity=".7"/><path d="M{x+29} {y}V{y+88}M{x} {y+45}H{x+58}" stroke="#17202e" stroke-width="7"/>' for x,y in [(292,546),(650,546),(472,460)])}
        <path d="M0 1030H1000" stroke="#111c2b" stroke-width="10"/>
        {''.join(f'<path d="M{x} 1050V890L{x+9} 875 {x+18} 890V1050" fill="#101a29"/>' for x in range(20,1000,48))}
        {tree(110,750,1.4,'#0b1524')}{tree(920,830,1.6,'#0b1524')}{person(500,975,.65)}"""
    if theme == "rooftop":
        bulbs = "".join(
            circle(
                x, 460 + int(40 * math.sin(x / 280)), 7, accent, 'filter="url(#glow)"'
            )
            for x in range(100, 950, 70)
        )
        return f"""{circle(650,300,146,accent,'opacity=".75"')}{skyline(rng,'#29445c',950,light)}
        <path d="M80 934 920 894 1000 1200H0Z" fill="#172f42"/>
        <rect x="350" y="490" width="410" height="266" fill="#ead4b8" stroke="#173044" stroke-width="18"/>
        <path d="M474 575 474 682 575 630Z" fill="{accent}"/>
        <path d="M85 448Q500 530 940 434" stroke="#182d42" stroke-width="3" fill="none"/>{bulbs}
        {person(386,849,.95)}{person(590,868,.9)}
        <path d="M340 876V960M421 876V960M548 891V968M622 891V968" stroke="#d29c75" stroke-width="7"/>
        <path d="M220 841 290 841 300 927H210Z" fill="{accent}"/><path d="M220 864H288M215 887H295" stroke="{light}" stroke-width="8"/>"""
    if theme == "clouds":
        clouds = "".join(
            circle(x, y, r, light, 'opacity=".16"')
            for x, y, r in [
                (80, 650, 180),
                (900, 700, 230),
                (550, 1000, 270),
                (100, 1080, 240),
            ]
        )
        return f"""{clouds}{circle(640,310,132,accent,'opacity=".8"')}
        <path d="M270 711Q510 605 740 711L580 995 400 959Z" fill="#5b7081"/>
        <ellipse cx="504" cy="710" rx="239" ry="69" fill="#8bbaa6"/>
        {tree(440,636,.7,'#28686b')}{tree(575,625,.9,'#28686b')}
        <path d="M175 421Q285 296 486 412L556 363 545 449 604 490 489 491Q343 548 175 421Z" fill="#c5dfe4"/>
        <path d="M242 440Q370 495 466 455" stroke="#699aaf" stroke-width="4" fill="none"/>{circle(223,418,8,'#264d68')}
        <path d="M344 463 387 537 424 467Z" fill="#86b3c5"/>
        {person(512,674,.48,'#1f4f62')}<path d="M478 613 502 590 528 613 502 634Z" fill="{accent}"/>"""
    if theme == "clock":
        ticks = "".join(
            line(
                570 + 255 * math.sin(i * math.pi / 6),
                480 - 255 * math.cos(i * math.pi / 6),
                570 + 280 * math.sin(i * math.pi / 6),
                480 - 280 * math.cos(i * math.pi / 6),
                light,
                6,
            )
            for i in range(12)
        )
        return f"""{circle(570,480,335,accent,'opacity=".08" filter="url(#glow)"')}
        {circle(570,480,310,'#142c3b',f'stroke="{accent}" stroke-width="8"')}
        {circle(570,480,290,'none',f'stroke="{accent}" stroke-width="2"')}{ticks}
        <path d="M570 480 480 315M570 480 735 416" stroke="{accent}" stroke-width="12" stroke-linecap="round" fill="none"/>
        {circle(570,480,18,light)}
        <path d="M190 1050 260 815H740L855 1050" fill="#142533"/>
        {''.join(f'<path d="M{240-i*16} {860+i*30}H{760+i*16}" stroke="{accent}" stroke-width="3" opacity=".4"/>' for i in range(8))}
        {person(520,830,.85)}{circle(230,365,83,'none',f'stroke="{light}" stroke-width="3" opacity=".4"')}
        <path d="M230 365V305L270 390" stroke="{light}" stroke-width="4" fill="none"/>"""
    return f"""{circle(670,290,170,accent,'opacity=".8"')}{mountains('#57736a',790)}{mountains('#304c45',980)}
        <path d="M340 1200C-40 1030 860 940 550 780L565 780C980 942 110 1090 820 1200Z" fill="#d6b894"/>
        <g transform="translate(530 855) rotate(6)"><rect x="-85" y="-65" width="170" height="120" rx="23" fill="{accent}"/><rect x="-65" y="-47" width="130" height="53" rx="8" fill="#355451"/>
        <path d="M0-47V6" stroke="{accent}" stroke-width="8"/>{circle(-52,35,9,light)}{circle(52,35,9,light)}
        <path d="M-72 50V73M72 50V73" stroke="#183b35" stroke-width="22"/></g>
        {tree(120,820,1.5,'#1b3c33')}{tree(920,880,1.8,'#1b3c33')}{tree(30,1020,1.5,'#18382f')}"""


def render(record, index, backdrop=False):
    title, slug, minutes, genres, rating, director, cast, description, theme, colors = (
        record
    )
    bg, accent, light = colors
    rng = random.Random(index * 173 + 37)
    stars = "".join(
        circle(
            rng.randrange(20, 980),
            rng.randrange(20, 800),
            rng.choice([1, 1, 1.5, 2]),
            light,
            f'opacity="{rng.uniform(.15,.65):.2f}"',
        )
        for _ in range(100)
    )
    art = scene(theme, colors, rng)
    defs = f"""<defs><linearGradient id="sky" x2=".75" y2="1"><stop stop-color="{bg}"/><stop offset=".62" stop-color="{bg}"/><stop offset="1" stop-color="{accent}" stop-opacity=".4"/></linearGradient>
    <radialGradient id="planet"><stop offset=".65" stop-color="{bg}"/><stop offset=".96" stop-color="{accent}"/><stop offset="1" stop-color="{light}"/></radialGradient>
    <linearGradient id="shade" x2="0" y2="1"><stop stop-color="{bg}" stop-opacity="0"/><stop offset="1" stop-color="{bg}"/></linearGradient>
    <filter id="glow" x="-100%" y="-100%" width="300%" height="300%"><feGaussianBlur stdDeviation="10"/></filter>
    <filter id="grain"><feTurbulence type="fractalNoise" baseFrequency=".7" numOctaves="3" stitchTiles="stitch"/></filter></defs>"""
    view = "0 130 1000 562.5" if backdrop else "0 0 1000 1500"
    head = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{view}" role="img"><title>{escape(title)} — авторска илюстрация</title>{defs}<rect x="-100" y="-100" width="1200" height="1800" fill="{bg}"/><rect width="1000" height="1500" fill="url(#sky)"/>{stars}{art}'
    if backdrop:
        return (
            head
            + '<rect width="1000" height="1100" filter="url(#grain)" opacity=".035"/></svg>'
        )
    words = title.upper().split()
    lines = []
    current = ""
    for word in words:
        if len(current + " " + word) > 18 and current:
            lines.append(current)
            current = word
        else:
            current = (current + " " + word).strip()
    lines.append(current)
    text = "".join(
        f'<text x="500" y="{1215+i*79}" text-anchor="middle" font-family="Arial, sans-serif" font-size="{70 if len(t)<16 else 60}" font-weight="700" letter-spacing="2" fill="#f5f1e9">{escape(t)}</text>'
        for i, t in enumerate(lines)
    )
    return (
        head
        + f"""<rect y="890" width="1000" height="400" fill="url(#shade)"/><rect y="1210" width="1000" height="290" fill="{bg}"/>
    <text x="500" y="78" text-anchor="middle" fill="{light}" font-family="Arial,sans-serif" font-size="19" letter-spacing="6">ПУКАНКОВ ОРИГИНАЛИ</text>
    <path d="M435 105H565" stroke="{accent}" stroke-width="2"/>
    <text x="500" y="1130" text-anchor="middle" fill="{accent}" font-family="Arial,sans-serif" font-size="18" letter-spacing="5">{escape(genres[0].upper())}</text>{text}
    <text x="500" y="1424" text-anchor="middle" fill="{light}" font-family="Arial,sans-serif" font-size="17" letter-spacing="3">ОРИГИНАЛНА ИСТОРИЯ · 2026</text>
    <text x="500" y="1460" text-anchor="middle" fill="{light}" opacity=".55" font-family="Arial,sans-serif" font-size="13" letter-spacing="2">ИЗМИСЛЕН ФИЛМ ЗА ДИПЛОМЕН ПРОЕКТ</text>
    <rect width="1000" height="1500" filter="url(#grain)" opacity=".035"/></svg>"""
    )


def main():
    target = ROOT / "public" / "images" / "originals"
    target.mkdir(parents=True, exist_ok=True)
    for i, record in enumerate(CONCEPTS):
        for kind in ("poster", "backdrop"):
            (target / f"{record[1]}-{kind}.svg").write_text(
                render(record, i, kind == "backdrop"), encoding="utf-8"
            )
    seats = []
    for row in range(6):
        y = 460 + row * 60
        w = 44 + row * 10
        for col in range(11):
            x = 800 + (col - 5) * (w + 15)
            seats.append(
                f'<rect x="{x-w/2}" y="{y}" width="{w}" height="{42+row*8}" rx="12" fill="#{90+row*5:02x}2430" stroke="#dc7a65" stroke-opacity=".17" stroke-width="2"/>'
            )
    cinema = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1600 900"><defs><radialGradient id="s"><stop stop-color="#ead5ad"/><stop offset="1" stop-color="#58727a"/></radialGradient></defs><rect width="1600" height="900" fill="#101722"/><path d="M0 0 360 230 1240 230 1600 0" fill="#1c2832"/><rect x="340" y="185" width="920" height="275" rx="18" fill="url(#s)"/><path d="M0 500 340 460 1260 460 1600 500V900H0Z" fill="#151822"/>{"".join(seats)}<path d="M170 900 470 465M1430 900 1130 465" stroke="#ffc928" stroke-width="4" opacity=".4"/></svg>'
    (target / "cinema.svg").write_text(cinema, encoding="utf-8")
    print(
        "Created 15 original posters, 15 matching backdrops and one cinema illustration."
    )


if __name__ == "__main__":
    main()
