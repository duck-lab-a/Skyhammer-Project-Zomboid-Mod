r"""The four descriptions with the F-22, the new cards and the CC BY credits (2026-11-26).

Reads main/vanilla_{en,ko}.txt as they are live, writes draft_2026-11-26\<same name>.
Card addresses come from draft_2026-11-26\urls.json {"main_01_apache": "https://i.ibb.co/..."};
a card without an address keeps its old picture (the F-22 card: a stand-in of the usual length).
"""
import json, sys
from pathlib import Path
H = Path(__file__).resolve().parent
D = H / 'draft_2026-11-26'
D.mkdir(exist_ok=True)
U = json.loads((D / 'urls.json').read_text('utf-8')) if (D / 'urls.json').exists() else {}
OLD = {'main_01_apache': '3YMwDTQ6/main-01-apache.jpg', 'main_02_a10': 'tSskgH5/main-02-a10.jpg',
       'main_03_ac130': 'vvwSHpV9/main-03-ac130.jpg', 'main_05_b2_nuke': 'n8mqjjPM/main-04-b2-nuke.jpg',
       'main_06_terminal_ko': 'TqwXqmRb/main-05-terminal.jpg',
       'vanilla_01_apache': 'p6h4fmgj/vanilla-01-apache.jpg', 'vanilla_02_a10': 'xKxgFmjR/vanilla-02-a10.jpg',
       'vanilla_03_ac130': 'QF9r7gL1/vanilla-03-ac130.jpg', 'vanilla_05_b2': 'TDgNpXL2/vanilla-04-b2-nuke.jpg',
       'vanilla_06_terminal_ko': 'hFfsR26y/vanilla-05-terminal.jpg'}


def f22(ed):
    return U.get(f'{ed}_04_f22', f'https://i.ibb.co/XXXXXXXX/{ed[0]}4.jpg')


def en(ed):
    R = []
    if ed == 'main':
        R += [("an [b]AC-130 gunship[/b] and a [b]B-2 bomber[/b] over the radio", "an [b]AC-130 gunship[/b], a flight of [b]F-22 Raptors[/b] and a [b]B-2 bomber[/b] over the radio"),
              ("Made for Build 42.21.", "Build 42.21+ (tested on 42.22)."),
              (", choosing the direction that catches the most infected, never one that passes near you.", ", in the direction that catches the most infected, never near you."),
              ("the same air support with no other mod needed. The aircraft show as shadows on the ground instead of 3D models, and it plays in [b]multiplayer[/b] (experimental). Enable only one of the two editions.", "the same air support with no other mod, aircraft as ground shadows, [b]multiplayer[/b] (experimental). Enable only one edition."),
              ("[h1]Compatibility[/h1]\n[list]\n[*]Tested alongside about 80 mods without observed conflicts.\n[/list]\n\n", ""),
              ("the gunner seat's own guns can hit them.\n", "the gunner seat's own guns can hit them.\n[*]Tested alongside about 80 mods without observed conflicts.\n"),
              ("3D models and Java: MIT. Artwork", '3D models (CC BY 4.0): "F22", "B2", "A10", "Ah64" by manilov.ap, "Lockheed AC-130 Hercules" by helijah. Java: MIT. Artwork')]
    else:
        R += [("unlock and call AH-64, A-10, AC-130 and B-2 support by radio", "unlock and call AH-64, A-10, AC-130, F-22 and B-2 support by radio"),
              ("Made for Build 42.21.", "Build 42.21+ (tested on 42.22)."),
              ("Shadows from Skyhammer's own 3D models (MIT). Artwork", 'Shadows made from 3D models (CC BY 4.0): "F22", "B2", "A10", "Ah64" by manilov.ap, "Lockheed AC-130 Hercules" by helijah. Artwork'),
              ("Found a bug? Please report it in Discussions.", "Bugs: Discussions."),
              ("Cooldowns and ammo are each player's own settings (held at the defaults with PvP on).", "Cooldowns and ammo are each player's own (defaults with PvP on)."),
              ("[*]Tested alongside about 80 mods without observed conflicts.", "[*]Tested with about 80 mods, no conflicts seen."),
              ("[b]Vanilla[/b]: no dependencies, ground shadows, multiplayer (experimental).\n", ""),
              ("[/url]: requires ZombieBuddy + Viewpoint, 3D aircraft, single player only. Enable only one edition.", "[/url]: ZombieBuddy + Viewpoint, 3D aircraft, single player. Enable only one edition."),
              ("only the air support radio opens it; K alone opens the quest log.", "only the air support radio opens it."),
              ("\n[*][b]Fallout[/b] hurts everyone standing in it, PvP or not.", "\n[*][b]Fallout[/b] hurts everyone, PvP or not.")]
    show = "Afterburners, roars, sonic booms and screen shake" if ed == 'main' else "Shadows, roars, sonic booms and screen shake"
    R += [("For the 105mm, the A-10 and the B-2, mark", "For the 105mm, the A-10, the F-22 and the B-2, mark"),
          ("[*]The nuke leaves fallout behind. Ground zero stays radioactive for days, and the longer you hang around the sicker you get. Stay too long and it can kill you even after you get out.", "[*]The nuke's ground zero stays radioactive for days. The longer you stay the sicker you get, and it can kill you even after you get out."),
          ("Prussian Blue capsules flush it out faster, but they won't save you if you stay in there.", "Prussian Blue capsules flush it out faster."),
          (" Targets under roofs are hidden; roof hits use roof height. Exit restores the camera.", " Targets under roofs are hidden."),
          ("[h2]Titan Zero-One - B-2[/h2]", f"[h2]Raven One-One - F-22[/h2]\n[img]{f22(ed)}[/img]\n[list]\n[*][b]Flight strike[/b]: mark one point and ten F-22s streak over at Mach speed, 0.4 s apart, dropping 20 heavy bombs on a 70x40-tile strip, in the direction that catches the most infected.\n[*]{show}. Vehicles in the strip are wrecked.\n[/list]\n\n[h2]Titan Zero-One - B-2[/h2]"),
          ("AC-130 150, B-2 300", "AC-130 150, F-22 200, B-2 300"),
          ("unlock all four aircraft", "unlock all five aircraft"),
          ("[tr][td]B-2[/td]", "[tr][td]F-22[/td][td]20 s / 3 min / 50 min[/td][td]1 strike, 20 bombs[/td][/tr]\n[tr][td]B-2[/td]")]
    return R


def ko(ed):
    R = []
    if ed == 'main':
        R += [("AH-64 아파치·A-10·AC-130·B-2를 부릅니다", "AH-64 아파치·A-10·AC-130·F-22 편대·B-2를 부릅니다"),
              ("42.21 기준입니다.", "42.21 이상(42.22 확인)용입니다."),
              ("[h1]바닐라 에디션 (멀티플레이)[/h1]\n[b][url=https://steamcommunity.com/sharedfiles/filedetails/?id=3813973682]Skyhammer Air Support - Vanilla Edition[/url][/b]: 다른 모드 없이 쓰는 같은 항공 지원입니다. 기체는 지면 그림자로 보이고 [b]멀티플레이[/b](실험적)를 지원합니다. 둘 중 하나만 켜세요.\n\n", ""),
              ("바닐라 에디션[/url][/b]을 받으세요.", "바닐라 에디션[/url][/b](지면 그림자)을 받으세요. 둘 중 하나만 켭니다."),
              ("[h1]호환성[/h1]\n[list]\n[*]약 80개 모드와 병용 시험에서 충돌이 관찰되지 않았습니다.\n[/list]\n\n", ""),
              ("초록색으로 표시됩니다(사수석 사격은 맞음).\n", "초록색으로 표시됩니다(사수석 사격은 맞음).\n[*]약 80개 모드와 함께 시험했고 충돌은 없었습니다.\n"),
              ("3D 모델·Java: MIT. 그림", '3D 모델(CC BY 4.0): manilov.ap "F22"·"B2"·"A10"·"Ah64", helijah "Lockheed AC-130 Hercules". Java: MIT. 그림'),
              ("[*]좀비 무리에 로켓을 퍼붓습니다(플레이어 근처는 피함).", "[*]플레이어 근처를 피해 좀비 무리에 로켓을 쏩니다.")]
    else:
        R += [("AH-64·A-10·AC-130·B-2를 부릅니다", "AH-64·A-10·AC-130·F-22·B-2를 부릅니다"),
              ("[h1]어느 에디션?[/h1]\n[b]바닐라[/b]: 추가 모드 없이 지면 그림자·멀티(실험적).\n[url=https://steamcommunity.com/sharedfiles/filedetails/?id=3813483790]Viewpoint[/url]: ZombieBuddy·Viewpoint 필요, 3D 기체·싱글. 하나만 켜세요.\n\n", ""),
              ("스카이해머[/url] 독립판:", "스카이해머(Viewpoint·3D판)[/url]의 독립판, 둘 중 하나만 켭니다."),
              ("항공 지원 무전기로만 열립니다(K 키: 퀘스트 일지).", "항공 지원 무전기로만 열립니다."),
              ("B42.21 싱글·멀티", "B42.21 이상(42.22 확인) 싱글·멀티"),
              ("그림자: 자체 3D 모델(MIT). 그림", '그림자 원본 모델(CC BY 4.0): manilov.ap "F22"·"B2"·"A10"·"Ah64", helijah "Lockheed AC-130 Hercules". 그림'),
              ("[*]약 80개 모드 병용 시험에서 충돌이 관찰되지 않았습니다.", "[*]약 80개 모드와 시험, 충돌 없음."),
              ("타이머는 [b]실시간[/b] 기준이며 싱글 일시정지 중에는 멈춥니다.", "타이머는 [b]실시간[/b], 싱글 일시정지 중엔 멈춥니다."),
              ("[*]낙진은 PvP와 상관없이 그 안에 있는 모두에게 해롭습니다.", "[*]낙진은 PvP와 상관없이 모두에게 해롭습니다."),
              ("[*]쿨타임과 탄약은 각자 설정합니다(PvP 중에는 기본값).", "[*]쿨타임·탄약은 각자 설정(PvP 중 기본값)."),
              ("기존 항공 지원 세이브는 아무 무전기로 사용 가능. 새 게임은 퀘스트부터 시작합니다.", "기존 항공 지원 세이브는 아무 무전기로 쓰고, 새 게임은 퀘스트부터입니다.")]
    show = "애프터버너·굉음·소닉붐·화면 흔들림" if ed == 'main' else "그림자·굉음·소닉붐·화면 흔들림"
    R += [("105mm, A-10, B-2는", "105mm, A-10, F-22, B-2는"),
          ("사격. 카메라 이동·탄도 표시, 지붕 아래 열원 차단·지붕 높이 착탄, 종료 시 시점 복원.", "사격. 지붕 아래 표적은 가려집니다."),
          ("[h2]타이탄 제로-원 - B-2[/h2]", f"[h2]레이븐 원-원 - F-22[/h2]\n[img]{f22(ed)}[/img]\n[list]\n[*][b]편대 폭격[/b]: 한 점을 찍으면 F-22 10대가 0.4초 간격, 마하 속도로 지나가며 좀비가 많은 방향의 70x40타일에 대형 폭탄 20발을 떨어뜨립니다.\n[*]{show}. 범위 안 차량은 부서집니다.\n[/list]\n\n[h2]타이탄 제로-원 - B-2[/h2]"),
          ("AC-130 150, B-2 300", "AC-130 150, F-22 200, B-2 300"),
          ("직접 잡은 좀비 한 마리당 1포인트이고(항공 지원 처치는 0), 포인트로 기체를 부릅니다(", "직접 잡은 좀비 1마리당 1포인트(항공 지원 처치는 0)로 기체를 부릅니다("),
          ("네 기체가 열립니다", "다섯 기체가 열립니다"),
          ("[tr][td]B-2[/td]", "[tr][td]F-22[/td][td]20초 / 3분 / 50분[/td][td]폭격 1회, 폭탄 20발[/td][/tr]\n[tr][td]B-2[/td]"),
          ("[*]폭심에 수일간 낙진이 남습니다. 피폭이 누적되면 밖으로 나온 뒤에도 사망할 수 있습니다.", "[*]폭심에 수일간 낙진이 남고, 피폭이 쌓이면 나온 뒤에도 죽을 수 있습니다."),
          ("[*]방호복·필터 방독면으로 보호하세요. 프러시안 블루는 방사능 배출을 돕지만 지속 노출은 막지 못합니다.", "[*]방호복·필터 방독면으로 막고, 프러시안 블루로 빨리 배출합니다.")]
    return R


bad = 0
for ed in ('main', 'vanilla'):
    for lg in ('en', 'ko'):
        n = f'{ed}_{lg}.txt'
        s = (H / n).read_text('utf-8').replace('\r\n', '\n')
        for a, b in (en if lg == 'en' else ko)(ed):
            c = s.count(a)
            if c != 1:
                print('!!', n, c, a[:60])
                bad += 1
            s = s.replace(a, b)
        for k, o in OLD.items():
            if not k.startswith(ed) or ('terminal' in k and lg == 'en'):   # the new terminal picture is the Korean one
                continue
            if k in U:
                s = s.replace('https://i.ibb.co/' + o, U[k])
        (D / n).write_bytes(s.encode('utf-8'))
        for k, o in OLD.items():           # (the size it will have with the short card names m1.jpg, v1.jpg, ...)
            if k.startswith(ed) and k not in U and not ('terminal' in k and lg == 'en'):
                s = s.replace('https://i.ibb.co/' + o, 'https://i.ibb.co/XXXXXXXX/m1.jpg')
        size = len(s.replace('\n', '\r\n').encode('utf-8'))
        print(n, size, 'OVER' if size > 7990 else 'ok')
sys.exit(1 if bad else 0)
