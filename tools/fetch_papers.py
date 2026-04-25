#!/usr/bin/env python3
import urllib.request
import json
import os
from pathlib import Path

target_dir = r"<PROJECT_ROOT>\Research Sources\Primary Sources"
Path(target_dir).mkdir(parents=True, exist_ok=True)

papers = [
    ("c28925939e873b4d3053dcd03a21694a5856009b", "Grand_Cliff_2004_Creatures_Entertainment"),
    ("a00e0ee918ed75559e960e3910092a4755b4ddf6", "Loyall_1997_Natural_Language_Believable"),
    ("4fef02f40bd630ecbb8236a36a582638ce810e97", "Tokui_2000_Music_Composition"),
    ("06578a0cd71b84197e5c05dbcc55facbbc46130a", "Bergen_2007_Adaptive_Reactive"),
    ("20de98dde566b34278c619b659a4beadd9e3a038", "Cliff_Grand_1998_Creatures_Global"),
    ("9b0dc882185f1cf799cf3ab694f4209e34e58957", "Blumberg_Galyean_1997_Control"),
    ("190eac03f40be2129e7cb67bc7e7caf36d40f5e6", "Shim_Kim_2003_Flying_Creatures"),
    ("04e186a459716c582eeb173174ef12724068ca7f", "Blumberg_Todd_1996_Bad_Dogs"),
    ("c35afb5bc08630a4019c81934fece64ddc63a168", "Miyata_1995_Genetic_Algorithm"),
    ("8443895fd995f0a162c1a78ae76974526e648cbb", "Wang_1998_Virtual_Life"),
    ("d030ae32ce6b4ed25bd36dda7ff659a7ae9df658", "Kukar_1997_Machine_Learning"),
    ("576b1137e8f8786dda9cbc0ad4bb077d1f1be8c5", "Lee_1997_Heat_Flux"),
    ("5d54211c78b2ed581043d0299f88d2bbe615b488", "Ventrella_2005_GenePool"),
    ("7d57fbb23d43c2021cb207fb4916aa3b6759cf33", "Shawver_1997_Virtual_Actors"),
    ("46e1984cde2545907a285cb412c6c97a0a5702ec", "Komosinski_1999_Framsticks"),
    ("abc9e7fb90c0a025483114f08e0ea6ad5d16dd69", "Maes_1995_Artificial_Life"),
    ("e1e81aa2fae3a857acb8ad8e0ba6020855430291", "Dai_2000_Control_v1"),
    ("20c2518c1cc364f3a1418e59d160b8c46a41b99c", "Lund_1997_Robot_Morphology"),
    ("215243d585f05f9b202a4245dbab1bc1f714b63a", "Kato_2000_Virtual_Cities"),
    ("cd95b6764d987e2e445760e8515a46d74c3e3f73", "Goldberg_1997_IMPROV"),
    ("4431c860fbe42c2f01d64f2a141f6d129bb43ad9", "Cliff_2003_Biologically_Inspired"),
    ("533d66f853c73ec3384981da8024ea41da8c66e8", "Schwelle_1989_Neural_Nets"),
    ("80f30d2f1875e7637bd79ad98f3d22aa05cd4136", "Badler_1997_Personalities"),
    ("2e508ce9c1d7aeb45c8bb3064213c6f2dadf833c", "Anderson_2002_Evolution"),
    ("b282dc0acffb66ef2a699432a0137e5c796d866d", "Krcah_2007_Evolving_Creatures"),
    ("bfe84faa21ca73a865ef1fbd598dc878dc183ebc", "Thalmann_2000_Virtual_Humans"),
    ("2d75cd33d5b885fe02ed0fdfbecc1675889ae6e2", "Ventrella_1998_Emergence"),
    ("e8c7b38e03308751c46531aef9ffc8d6de4caedb", "Becheiraz_1998_Animation"),
    ("c055784a0b594e45d851a5035a99df6969544e09", "Bergen_1998_Learning"),
    ("9d972c75bf45b75f7360fced48b412b09bf9cfff", "Greenfield_1998_Communication"),
    ("76c09bc7aeb721b6f3c99791ace0c88eb5089903", "Zhou_2006_Control_Creatures"),
    ("7b1acf73d76a740b4bfbf326d692ff911b106920", "Dai_2000_Control_v3"),
    ("1217744173bde28ab7924601cc678bc2502e04df", "Lee_1996_Hybrid_GP"),
    ("45a0ef5efb2f1010945553a2e234edaeadbdbf8d", "Ochoa_1998_Lindenmayer"),
    ("71d6d7a785a5246f95436364684981de2241efba", "Komosinski_2000_Framsticks_World"),
    ("9e9970f0d01ca87980ca248b09c25ca86e6e4929", "Ventrella_1995_Disney_Darwin"),
    ("3dcd3b162eb95e63040edcbd345f5821c178be9e", "Taylor_2000_Evolution_Morphologies"),
    ("5fcee4e413d4285036d8b7dcf5391779d7b8f367", "Sanza_1999_Classifier"),
    ("cfa9a25bff237a9710c638304fcf9d187a076045", "Westendorp_1998_Reasoning"),
    ("96f4a8d61b8bde892a2f227e8226087cadc9f929", "Buendia_2000_Digital_Creatures"),
]

downloaded = []
failed = []

for s2_id, fname in papers:
    pdf_path = f"{target_dir}/{fname}.pdf"
    if os.path.exists(pdf_path):
        print(f"[OK] {fname} (exists)")
        continue

    # Try SemanticScholar API
    try:
        url = f"https://api.semanticscholar.org/graph/v1/paper/{s2_id}?fields=openAccessPdf"
        req = urllib.request.Request(url, headers={'User-Agent': 'NORNBRAIN'})
        resp = urllib.request.urlopen(req, timeout=5)
        data = json.loads(resp.read())
        if data.get('openAccessPdf', {}).get('url'):
            pdf_url = data['openAccessPdf']['url']
            urllib.request.urlretrieve(pdf_url, pdf_path)
            print(f"[OK] {fname}")
            downloaded.append(fname)
            continue
    except Exception as e:
        pass

    failed.append(fname)
    print(f"[XX] {fname} (not found)")

print(f"\n=== Summary ===")
print(f"Downloaded: {len(downloaded)}")
print(f"Failed: {len(failed)}")
if failed:
    print(f"Failed list: {', '.join(failed[:5])}{'...' if len(failed) > 5 else ''}")
