EMOJI_MAPPING = {
    # Rarity
    'R': '<:R_:1347121611832164352>',
    'SR': '<:Sr:1347121626763755560>',
    'SSR': '<:Ssr:1347121643029266534>',
    # Class
    'Attacker': '<:Attacker:1347172718482554930>',
    'Defender': '<:Defender:1347172728767254590>',
    'Supporter': '<:Supporter:1347172743845777509>',
    # Burst
    'I': '<:Burst1:1347172759708368936>',
    'II': '<:Burst2:1347172769074516018>',
    'III': '<:Burst3:1347172780809912340>',
    'All': '<:BurstAll:1347172791946051594>',
    # Manufacturer
    'Elysion': '<:Elysion_Icon:1347172814796623952>',
    'Missilis': '<:Missilis_Icon:1347172829304590376>',
    'Tetra': '<:Tetra_Icon:1347172846270414891>',
    'Pilgrim': '<:Pilgrim_Icon:1347172860732375060>',
    # Weapon
    'AR': '<:ar:1347173993756753930>',
    'MG': '<:mg:1347174014207922196>',
    'RL': '<:rl:1347174027348807803>',
    'SG': '<:sg:1347174041294868540>',
    'SMG': '<:smg:1347174054452265011>',
    'SNR': '<:sr:1347174065713975316>',
    # Element
    'Wind': '<:wind:1347175032203247626>',
    'Iron': '<:iron:1347175057205755905>',
    'Fire': '<:fire:1347175079330578453>',
    'Water': '<:water:1347175102198059078>',
    'Electric': '<:electric:1347175120216657970>'
}

MAX_LIMIT_BREAKS = {
    "R": 0,
    "SR": 2,
    "SSR": 3
}

# Level caps based on limit breaks
LEVEL_CAPS = {
    "R": 80,  # R NIKKEs max at 80 regardless of limit breaks
    "SR": {  # SR level caps based on limit breaks
        0: 80,
        1: 120,
        2: 160
    },
    "SSR": {  # SSR level caps based on limit breaks
        0: 80,
        1: 120,
        2: 160,
        3: 200
    }
}

STARTING_NIKKES = {
    "anis": {"rarity": "SR", "limit_break": 0, "level": 1},
    "product 08": {"rarity": "R", "limit_break": 0, "level": 1},
    "rapi": {"rarity": "SR", "limit_break": 0, "level": 1},
    "neon": {"rarity": "SR", "limit_break": 0, "level": 1},
    "idoll ocean": {"rarity": "R", "limit_break": 0, "level": 1},
    "soldier fa": {"rarity": "R", "limit_break": 0, "level": 1}
}

MOLD_EMOJIS = {
    'mid': '<:moldmid:1346664136112865392>',
    'high': '<:moldhigh:1346664186213699655>',
    'elysion': '<:moldely:1346664226038747198>',
    'missilis': '<:moldmis:1346664253964288032>',
    'tetra': '<:moldtet:1346664359060836352>',
    'pilgrim': '<:moldpil:1346664403445092454>'
}

MOLD_RATES = {
    'mid': {
        'SSR': 0.21,  # 21% non-limited non-Pilgrim SSR
        'SR': 0.79,   # 79% non-limited SR (fixed from 0.09)
        'R': 0.00     # 0% R (fixed from 0.70)
    },
    'high': {
        'SSR': 0.61,  # 61% non-limited non-Pilgrim SSR
        'SR': 0.39,   # 39% non-limited SR
        'R': 0.00     # No R
    },
    'elysion': {
        'SSR': 0.50,  # 50% non-limited manufacturer SSR
        'SR': 0.30,   # 30% non-limited manufacturer SR
        'R': 0.20     # 20% any R
    },
    'missilis': {
        'SSR': 0.50,
        'SR': 0.30,
        'R': 0.20
    },
    'tetra': {
        'SSR': 0.50,
        'SR': 0.30,
        'R': 0.20
    },
    'pilgrim': {
        'SSR': 0.50,
        'SR': 0.30,
        'R': 0.20
    }
}

STARTING_MOLDS = {
    'mid': 0,
    'high': 0,
    'elysion': 0,
    'missilis': 0,
    'tetra': 0,
    'pilgrim': 0
}

# Currency emoji mappings
CURRENCY_EMOJIS = {
    'battle_data': '<:battledataset:1347015196736225310>',
    'core_dust': '<:coredust:1347015208513703937>'
}
