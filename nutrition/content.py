"""Belajar Gizi: the chapters, the cards and the quiz questions.

Content lives in the repo, not the database, on purpose. These are health
claims about real food, so they go through code review like everything else,
and a wrong number gets caught before a member reads it. Editing needs a
deploy, which is the right amount of friction for this kind of text.

Two rules when adding to this file:

1. **Every number is an estimate and says so.** Portions and prices vary by
   warung. Round hard, write "kira-kira", and never imply a precision nobody
   has. `PRICE_NOTE` carries the date and the caveat for the price chart.
2. **A quiz `key` is permanent.** It is stored on every recorded answer, so
   renaming one orphans the history behind that question. Reorder freely,
   rename never.
"""

from urllib.parse import quote

# Prices behind the "protein per Rp 10.000" chart. The one thing here that
# goes stale, so it sits in one place with a date on it.
PRICE_NOTE = "Perkiraan harga pasar Bandung, awal 2026. Angkanya bisa geser, urutannya nggak."

DISCLAIMER = (
    "Ini panduan umum buat orang sehat, bukan saran medis. Kalau kamu punya "
    "kondisi khusus (diabetes, hamil, darah tinggi, atau sedang minum obat "
    "tertentu), enaknya tanya dokter dulu."
)

GYM_WHATSAPP_NUMBER = "628996940908"

# Level names by number of finished chapters. The last name covers everything
# beyond it, so adding a chapter later cannot leave a member without a level.
LEVELS = [
    "Baru Mulai",
    "Mulai Paham",
    "Lumayan Jago",
    "Melek Gizi",
]

# A perfect run gets emas, a decent one perak, finishing at all gets perunggu.
MEDAL_PERAK_AT = 0.6


CHAPTERS = [
    {
        "slug": "kalori",
        "number": 1,
        "title": "Kalori",
        "subtitle": "Kenapa berat badan naik atau turun",
        "icon": "fas fa-scale-balanced",
        "minutes": 4,
        "blocks": [
            {
                "type": "card",
                "title": "Badan kamu cuma ngitung satu hal",
                "body": [
                    "Berat badan naik atau turun itu soal satu hal: kalori yang masuk "
                    "dibanding kalori yang kepakai. Bukan soal jam makan, bukan soal "
                    "nasi putih atau nasi merah.",
                    "Masuknya lebih banyak, berat naik. Masuknya lebih sedikit, berat "
                    "turun. Sesederhana itu, walaupun ngejalaninnya nggak selalu gampang.",
                ],
            },
            {
                "type": "card",
                "title": "Kalori nggak kelihatan dari porsinya",
                "body": [
                    "Semangkok sayur bening kira-kira 50 kalori. Dua bala-bala yang "
                    "ukurannya seuprit bisa 250 kalori.",
                    "Yang bikin kalori padat itu minyak dan gula. Sialnya, dua-duanya "
                    "paling nggak bikin kenyang.",
                ],
                "highlight": "1 gram minyak = 9 kalori. 1 gram protein atau karbo = 4 kalori.",
            },
            {
                "type": "swap",
                "title": "Piring yang sama, warung yang sama",
                "note": "Perkiraan, porsi warung standar.",
                "before": {
                    "label": "Sebelum",
                    "items": ["Nasi 1 porsi", "2 bala-bala", "Sambal + kerupuk", "Es teh manis"],
                    "kcal": 600,
                    "protein": 9,
                },
                "after": {
                    "label": "Sesudah",
                    "items": ["Nasi 1 porsi", "Ayam bakar 1 potong", "Tumis sayur", "Es teh tawar"],
                    "kcal": 520,
                    "protein": 28,
                },
                "caption": "Porsinya sama-sama penuh. Kalorinya malah turun, proteinnya naik 3 kali lipat.",
            },
            {
                "type": "quiz",
                "key": "kalori-1",
                "question": "Kamu makan di warteg. Mana yang paling banyak kalorinya?",
                "choices": [
                    {"key": "a", "text": "1 potong ayam bakar"},
                    {"key": "b", "text": "2 bala-bala + 1 es teh manis"},
                    {"key": "c", "text": "1 mangkok sayur asem"},
                ],
                "answer": "b",
                "explanation": (
                    "Gorengan nyerep minyak, dan es teh manis nambah 100 kalori lebih "
                    "tanpa bikin kenyang sedikit pun. Dua-duanya bareng kira-kira 350 "
                    "kalori. Ayam bakar sekitar 200 kalori, dan itu yang paling "
                    "ngenyangin karena proteinnya tinggi."
                ),
            },
            {
                "type": "card",
                "title": "Yang bikin kebobolan biasanya bukan nasinya",
                "body": [
                    "Nasi paling sering disalahin, padahal 1 porsi kira-kira 250 kalori "
                    "dan bikin kenyang.",
                    "Yang jarang dihitung: minyak buat gorengan, gula di minuman, "
                    "kerupuk, dan saus kemasan. Semuanya nambah kalori tanpa nambah rasa kenyang.",
                ],
            },
            {
                "type": "quiz",
                "key": "kalori-2",
                "question": "Mana yang paling gampang bikin kalori sehari kebobolan tanpa kerasa?",
                "choices": [
                    {"key": "a", "text": "Nasi nambah setengah porsi"},
                    {"key": "b", "text": "1 es kopi susu gula aren"},
                    {"key": "c", "text": "1 telur rebus"},
                ],
                "answer": "b",
                "explanation": (
                    "Kopi susu gula aren kira-kira 250 kalori dan habis dalam 2 menit. "
                    "Nasi setengah porsi cuma sekitar 125 kalori dan bikin kenyang. "
                    "Telur rebus sekitar 75 kalori dan isinya protein."
                ),
            },
            {
                "type": "card",
                "title": "Kamu nggak perlu ngitung seumur hidup",
                "body": [
                    "Nggak usah nimbang tiap suapan. Cukup tau mana yang padat kalori "
                    "(gorengan, minuman manis, kerupuk, mayones) dan mana yang ngenyangin "
                    "(protein, sayur, nasi secukupnya).",
                    "Ubah dua tiga kebiasaan yang paling sering kamu lakuin, itu udah "
                    "ngefek lebih besar daripada diet ketat yang cuma tahan seminggu.",
                ],
            },
            {
                "type": "quiz",
                "key": "kalori-3",
                "question": (
                    "Kamu mau turun berat badan tapi tetep makan di warung deket rumah. "
                    "Langkah mana yang paling ngefek?"
                ),
                "choices": [
                    {"key": "a", "text": "Ganti nasi putih jadi nasi merah"},
                    {"key": "b", "text": "Lauknya bakar atau rebus, minumnya tawar"},
                    {"key": "c", "text": "Skip makan malam"},
                ],
                "answer": "b",
                "explanation": (
                    "Nasi merah vs nasi putih bedanya kecil banget, cuma serat sedikit "
                    "lebih banyak. Skip makan malam bikin kelaperan malem dan biasanya "
                    "balas dendam besoknya. Ganti cara masak lauk plus minuman tawar itu "
                    "bisa motong 300 sampai 500 kalori sehari, dan porsi makanmu tetep."
                ),
            },
            {
                "type": "quiz",
                "key": "kalori-4",
                "question": (
                    "Kamu udah latihan 4x seminggu tapi berat badan nggak turun. "
                    "Paling mungkin kenapa?"
                ),
                "choices": [
                    {"key": "a", "text": "Latihannya kurang keras"},
                    {"key": "b", "text": "Makannya masih lebih banyak dari yang kepakai"},
                    {"key": "c", "text": "Metabolismenya rusak"},
                ],
                "answer": "b",
                "explanation": (
                    "Satu jam latihan kira-kira 200 sampai 400 kalori, dan itu gampang "
                    "banget ketutup 1 kopi susu plus gorengan. Latihan itu buat bikin "
                    "otot dan bikin badan sehat; yang nentuin berat badan tetep makannya. "
                    "\"Metabolisme rusak\" hampir nggak pernah jadi penyebabnya."
                ),
            },
        ],
    },
    {
        "slug": "protein",
        "number": 2,
        "title": "Protein",
        "subtitle": "Yang paling sering kurang, dan paling murah",
        "icon": "fas fa-egg",
        "minutes": 5,
        "blocks": [
            {
                "type": "card",
                "title": "Nasi banyak, lauk dikit",
                "body": [
                    "Dari semua soal makan, protein yang paling sering kurang di sini. "
                    "Piring standar kita: nasi menggunung, lauknya sepotong kecil.",
                    "Padahal protein yang bikin otot kebentuk, bikin kenyang lebih lama, "
                    "dan bikin badan nggak kendor waktu berat badan turun.",
                ],
            },
            {
                "type": "card",
                "title": "Butuh berapa banyak?",
                "body": [
                    "Patokan gampang buat yang latihan: kira-kira 1,6 gram protein per "
                    "kilo berat badan. Berat 60 kg berarti sekitar 95 gram sehari.",
                    "Kedengeran banyak? Sehari bisa kayak gini: 2 telur pagi (13 g), "
                    "ayam sepotong + tempe siang (35 g), susu segelas sore (8 g), ikan + "
                    "tahu malem (28 g), plus nasinya sendiri (10 g). Total sekitar 94 gram.",
                ],
                "highlight": "Berat badan (kg) x 1,6 = target protein harian dalam gram.",
            },
            {
                "type": "bars",
                "title": "Protein per Rp 10.000",
                "unit": "gram protein",
                "note": PRICE_NOTE,
                "rows": [
                    {"label": "Tempe", "value": 80},
                    {"label": "Ayam dada", "value": 45},
                    {"label": "Tahu", "value": 40},
                    {"label": "Susu bubuk", "value": 35},
                    {"label": "Telur", "value": 32},
                    {"label": "Ikan kembung", "value": 30},
                    {"label": "Susu UHT", "value": 17},
                    {"label": "Whey protein", "value": 16, "muted": True},
                ],
                "caption": (
                    "Whey itu cuma protein yang dibikin praktis. Nggak salah, cuma paling "
                    "mahal per gramnya. Tempe dan telur ngalahin suplemen jauh."
                ),
            },
            {
                "type": "quiz",
                "key": "protein-1",
                "question": (
                    "Menu kamu hari ini: nasi 2 porsi, sayur, 2 bala-bala, sambal, "
                    "es teh manis. Kira-kira dapet protein berapa?"
                ),
                "choices": [
                    {"key": "a", "text": "Sekitar 10 sampai 15 gram"},
                    {"key": "b", "text": "Sekitar 30 gram"},
                    {"key": "c", "text": "Sekitar 60 gram"},
                ],
                "answer": "a",
                "explanation": (
                    "Hampir semua kalorinya dari karbo dan minyak. Buat orang 60 kg yang "
                    "latihan, sehari segini baru sekitar 15% dari kebutuhan. Kalorinya "
                    "udah masuk banyak, bahan buat ototnya hampir nggak ada."
                ),
            },
            {
                "type": "quiz",
                "key": "protein-2",
                "question": "Mana sumber protein paling murah per gramnya?",
                "choices": [
                    {"key": "a", "text": "Whey protein"},
                    {"key": "b", "text": "Tempe"},
                    {"key": "c", "text": "Ayam dada"},
                    {"key": "d", "text": "Susu UHT"},
                ],
                "answer": "b",
                "explanation": (
                    "Tempe kira-kira 19 gram protein per 100 gram, dengan harga yang "
                    "nggak ada lawan. Uang Rp 10.000 di tempe dapet kira-kira 5 kali "
                    "lipat protein dibanding Rp 10.000 di whey."
                ),
            },
            {
                "type": "quiz",
                "key": "protein-3",
                "question": "Kamu latihan rutin 3 bulan tapi otot nggak kelihatan nambah. Paling mungkin yang kurang?",
                "choices": [
                    {"key": "a", "text": "Protein dan makan yang cukup"},
                    {"key": "b", "text": "Suplemen"},
                    {"key": "c", "text": "Durasi latihan, harusnya 2 jam"},
                ],
                "answer": "a",
                "explanation": (
                    "Latihan itu sinyalnya, makanan itu bahannya. Sinyal terus tapi "
                    "bahannya nggak ada, ototnya nggak kebentuk. Nambah durasi latihan "
                    "tanpa nambah makan malah bikin makin capek doang."
                ),
            },
            {
                "type": "card",
                "title": "Cara naikin protein tanpa ribet",
                "body": [
                    "Satu: tiap makan besar, tentuin lauk proteinnya dulu, nasinya nyusul.",
                    "Dua: tambah 1 telur ke sarapan. Tiga: tempe atau tahu di tiap makan, "
                    "jadi lauk, bukan cuma pelengkap. Empat: kalau biasa minum manis, "
                    "ganti susu, sekalian dapet 8 gram protein.",
                ],
            },
            {
                "type": "quiz",
                "key": "protein-4",
                "question": "Buat yang tujuannya turun berat badan, protein itu...",
                "choices": [
                    {"key": "a", "text": "Nggak penting, yang penting kalorinya dikit"},
                    {"key": "b", "text": "Makin penting, biar yang turun lemaknya bukan ototnya"},
                    {"key": "c", "text": "Cuma buat yang mau badan gede"},
                ],
                "answer": "b",
                "explanation": (
                    "Waktu kalori dikurangin, badan bisa ngambil dari otot juga. Protein "
                    "yang cukup plus latihan beban bikin yang kepake itu lemaknya. "
                    "Bonusnya, protein paling bikin kenyang, jadi nahan laper lebih gampang."
                ),
            },
        ],
    },
    {
        "slug": "gula-cair",
        "number": 3,
        "title": "Gula Cair",
        "subtitle": "Kalori yang masuk paling gampang",
        "icon": "fas fa-mug-hot",
        "minutes": 4,
        "blocks": [
            {
                "type": "card",
                "title": "Diminum 2 menit, kalorinya sepiring makan",
                "body": [
                    "Minuman manis itu kalori yang nggak bikin kenyang sama sekali. "
                    "Es teh manis, kopi susu gula aren, boba, jus pakai kental manis.",
                    "Badan kamu nggak ngitung minuman kayak dia ngitung makanan. Abis "
                    "minum 400 kalori, kamu masih laper kayak sebelumnya.",
                ],
            },
            {
                "type": "bars",
                "title": "Kira-kira kalori per gelas",
                "unit": "kalori",
                "note": "Perkiraan, tergantung takaran gula tiap warung.",
                "rows": [
                    {"label": "Boba milk tea 500ml", "value": 400},
                    {"label": "Jus alpukat + SKM", "value": 380},
                    {"label": "Kopi susu gula aren", "value": 250},
                    {"label": "Es teh manis", "value": 110},
                    {"label": "Es teh tawar", "value": 0},
                    {"label": "Nasi + ayam bakar (pembanding)", "value": 460, "muted": True},
                ],
                "caption": (
                    "Baris terakhir bukan minuman, itu pembanding. Satu boba plus satu "
                    "kopi susu udah lebih dari sepiring makan lengkap, tapi nggak ada "
                    "protein dan nggak bikin kenyang."
                ),
            },
            {
                "type": "quiz",
                "key": "gula-1",
                "question": "Satu es kopi susu gula aren kira-kira setara apa?",
                "choices": [
                    {"key": "a", "text": "1 potong tempe goreng"},
                    {"key": "b", "text": "Sepiring nasi + ayam bakar"},
                    {"key": "c", "text": "1 mangkok sayur"},
                ],
                "answer": "b",
                "explanation": (
                    "Kira-kira 250 kalori, hampir semuanya dari gula dan krimer. "
                    "Bedanya, sepiring nasi + ayam bakar ngasih kamu 25 gram protein "
                    "dan bikin kenyang sampai sore."
                ),
            },
            {
                "type": "card",
                "title": "Kental manis itu bukan susu",
                "body": [
                    "Susu kental manis kira-kira separuhnya gula. Proteinnya cuma sekitar "
                    "1 sampai 2 gram per 2 sendok makan, gulanya belasan gram.",
                    "Namanya susu, isinya lebih dekat ke sirup. Kalau kamu mau protein "
                    "dari susu, pakai susu cair atau susu bubuk full cream.",
                ],
                "highlight": "Kental manis: gula belasan gram, protein 1 sampai 2 gram per 2 sdm.",
            },
            {
                "type": "quiz",
                "key": "gula-2",
                "question": "Kamu tetep pengen ngopi tiap hari. Yang paling masuk akal?",
                "choices": [
                    {"key": "a", "text": "Berhenti ngopi total"},
                    {"key": "b", "text": "Minta setengah gula atau tanpa gula, susunya susu asli"},
                    {"key": "c", "text": "Ganti ke boba biar nggak bosen"},
                ],
                "answer": "b",
                "explanation": (
                    "Yang bisa kamu jalanin bertahun-tahun itu yang menang. Setengah gula "
                    "aja udah motong 100 kalori lebih per gelas, dan lidah kamu nyesuain "
                    "dalam 2 minggu. Boba malah lebih tinggi kalorinya."
                ),
            },
            {
                "type": "quiz",
                "key": "gula-3",
                "question": "Jus buah itu...",
                "choices": [
                    {"key": "a", "text": "Selalu sehat, sebanyak apa pun"},
                    {"key": "b", "text": "Oke kalau tanpa gula dan SKM, tapi buah utuh lebih ngenyangin"},
                    {"key": "c", "text": "Sama jeleknya kayak soda"},
                ],
                "answer": "b",
                "explanation": (
                    "Masalah jus di sini biasanya bukan buahnya, tapi gula dan kental "
                    "manis yang ditambahin. Buah utuh menang karena seratnya masih ada, "
                    "jadi lebih ngenyangin, dan gulanya masuk lebih pelan."
                ),
            },
            {
                "type": "quiz",
                "key": "gula-4",
                "question": (
                    "Kamu biasa 2 es teh manis + 1 kopi susu tiap hari. Mana yang paling ngefek?"
                ),
                "choices": [
                    {"key": "a", "text": "Nambah cardio 30 menit tiap hari"},
                    {"key": "b", "text": "Ganti 2 dari 3 minuman itu jadi tawar"},
                    {"key": "c", "text": "Ganti nasi putih jadi nasi merah"},
                ],
                "answer": "b",
                "explanation": (
                    "Dua dari tiga minuman itu kira-kira 350 kalori. Buat ngebakar segitu "
                    "kamu perlu jalan cepat sejam lebih, tiap hari. Nggak minumnya jauh "
                    "lebih gampang daripada ngebakarnya."
                ),
            },
        ],
    },
]


def chapters():
    """Every chapter, with the counts the templates need."""
    result = []
    for chapter in CHAPTERS:
        result.append(
            dict(
                chapter,
                quiz_count=sum(1 for b in chapter["blocks"] if b["type"] == "quiz"),
                step_count=len(chapter["blocks"]),
            )
        )
    return result


def get_chapter(slug):
    for chapter in chapters():
        if chapter["slug"] == slug:
            return chapter
    return None


def next_chapter(slug):
    slugs = [c["slug"] for c in CHAPTERS]
    if slug not in slugs:
        return None
    position = slugs.index(slug) + 1
    return get_chapter(slugs[position]) if position < len(slugs) else None


def total_chapters():
    return len(CHAPTERS)


def grade(chapter, answers):
    """Grade a submitted {question key: choice key} map against the content.

    Graded here rather than trusting the browser: the quiz reveals the answer
    on the spot, so the page already knows them, and the recorded score should
    still mean something.
    """
    graded = []
    for block in chapter["blocks"]:
        if block["type"] != "quiz":
            continue
        chosen = answers.get(block["key"])
        graded.append(
            {
                "key": block["key"],
                "chosen": chosen,
                "correct": chosen == block["answer"],
            }
        )
    return graded


def medal(correct, total):
    if not total:
        return None
    if correct == total:
        return "emas"
    if correct / total >= MEDAL_PERAK_AT:
        return "perak"
    return "perunggu"


def level_name(chapters_done):
    if chapters_done < 0:
        chapters_done = 0
    return LEVELS[min(chapters_done, len(LEVELS) - 1)]


def trainer_whatsapp_url(chapter_title):
    message = (
        f"Halo Mulai Gym, aku abis baca Belajar Gizi bab {chapter_title}. "
        "Mau tanya soal makan buat program aku."
    )
    return f"https://wa.me/{GYM_WHATSAPP_NUMBER}?text={quote(message)}"


def share_whatsapp_url(chapter_title, url):
    message = (
        f"Aku baru selesai bab {chapter_title} di Belajar Gizi Mulai Gym. "
        f"Coba juga, lumayan bikin melek: {url}"
    )
    return f"https://wa.me/?text={quote(message)}"
