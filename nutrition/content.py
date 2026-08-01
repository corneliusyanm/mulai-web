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

# Levels by number of finished chapters, as bands rather than one name per
# chapter: with eight chapters that would be nine names nobody can tell apart.
# `min` is inclusive and the last band covers everything beyond it, so adding a
# chapter later cannot leave a member without a level.
LEVELS = [
    {"min": 0, "name": "Baru Mulai"},
    {"min": 1, "name": "Mulai Paham"},
    {"min": 3, "name": "Lumayan Jago"},
    {"min": 6, "name": "Jago Gizi"},
    {"min": 9, "name": "Melek Gizi"},
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
        "emoji": "⚖️",
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
        "emoji": "🥚",
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
                    {"label": "Tempe", "value": 60},
                    {"label": "Ayam dada", "value": 36},
                    {"label": "Tahu", "value": 30},
                    {"label": "Telur", "value": 26},
                    {"label": "Ikan kembung", "value": 24},
                    {"label": "Whey protein", "value": 16, "muted": True},
                    {"label": "Susu UHT", "value": 13},
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
        "emoji": "🧋",
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
    {
        "slug": "gorengan",
        "number": 4,
        "title": "Gorengan & Minyak",
        "subtitle": "Kenapa yang kecil bisa paling padat",
        "icon": "fas fa-fire-burner",
        "emoji": "🍤",
        "minutes": 4,
        "blocks": [
            {
                "type": "card",
                "title": "Minyak itu kalori paling padat",
                "body": [
                    "Satu sendok makan minyak kira-kira 120 kalori. Nggak nambah rasa "
                    "kenyang, nggak nambah protein, tapi masuk ke hampir semua yang kita "
                    "makan di luar.",
                    "Waktu digoreng, makanan nyerep minyaknya. Makanya gorengan yang "
                    "kelihatan kecil bisa lebih berat kalorinya daripada sepotong ayam.",
                ],
                "highlight": "1 sendok makan minyak = kira-kira 120 kalori, dan minyaknya nggak kelihatan.",
            },
            {
                "type": "bars",
                "title": "Kira-kira kalori per potong",
                "unit": "kalori",
                "note": "Perkiraan, tergantung ukuran dan minyaknya.",
                "rows": [
                    {"label": "Ayam goreng tepung", "value": 350},
                    {"label": "Pisang goreng", "value": 140},
                    {"label": "Bala-bala", "value": 120},
                    {"label": "Cireng", "value": 90},
                    {"label": "Tempe goreng", "value": 80},
                    {"label": "Tahu goreng", "value": 60},
                    {"label": "Ayam bakar (pembanding)", "value": 200, "muted": True},
                ],
                "caption": (
                    "Ayam yang sama, dua cara masak, bedanya kira-kira 150 kalori per "
                    "potong. Dan yang dibakar proteinnya sama."
                ),
            },
            {
                "type": "quiz",
                "key": "gorengan-1",
                "question": "Ayam goreng tepung dibanding ayam bakar, sepotong bedanya kira-kira?",
                "choices": [
                    {"key": "a", "text": "Mirip aja"},
                    {"key": "b", "text": "Yang digoreng sekitar 150 kalori lebih banyak"},
                    {"key": "c", "text": "Yang dibakar lebih banyak"},
                ],
                "answer": "b",
                "explanation": (
                    "Tepungnya nyerep minyak, dan minyak itu 9 kalori per gram. Ayamnya "
                    "sendiri sama, jadi kamu bayar 150 kalori cuma buat cara masaknya."
                ),
            },
            {
                "type": "swap",
                "title": "Ayam yang sama, dua piring",
                "note": "Perkiraan, porsi warung standar.",
                "before": {
                    "label": "Sebelum",
                    "items": ["Nasi 1 porsi", "Ayam goreng tepung", "Kerupuk", "Es teh manis"],
                    "kcal": 750,
                    "protein": 25,
                },
                "after": {
                    "label": "Sesudah",
                    "items": ["Nasi 1 porsi", "Ayam bakar", "Tumis sayur", "Es teh tawar"],
                    "kcal": 510,
                    "protein": 27,
                },
                "caption": "Lauknya tetep ayam, porsinya tetep sepiring penuh. Yang hilang cuma minyak dan gula.",
            },
            {
                "type": "quiz",
                "key": "gorengan-2",
                "question": "Bala-bala kelihatan kecil, jadi...",
                "choices": [
                    {"key": "a", "text": "Aman, karena porsinya kecil"},
                    {"key": "b", "text": "Tetep padat kalori, karena nyerep minyak"},
                    {"key": "c", "text": "Nggak ada kalorinya, isinya sayur"},
                ],
                "answer": "b",
                "explanation": (
                    "Isinya memang sayur dan tepung, tapi yang bikin kalorinya naik itu "
                    "minyak yang keserep. Dua bala-bala bisa setara seporsi nasi, tapi "
                    "kenyangnya jauh lebih cepet hilang."
                ),
            },
            {
                "type": "card",
                "title": "Ganti cara masak, bukan ganti lauk",
                "body": [
                    "Kamu nggak harus ganti menu. Ayam tetep ayam, ikan tetep ikan. Yang "
                    "diganti cuma cara masaknya: bakar, kukus, rebus, atau tumis pakai "
                    "minyak sedikit.",
                    "Ini paling gampang dijalanin di warung, karena kamu cuma perlu milih "
                    "lauk yang nggak digoreng, bukan pesen menu khusus.",
                ],
            },
            {
                "type": "quiz",
                "key": "gorengan-3",
                "question": "Kamu tetep suka gorengan. Yang paling masuk akal?",
                "choices": [
                    {"key": "a", "text": "Berhenti total, gorengan haram"},
                    {"key": "b", "text": "Jadiin camilan kadang-kadang, bukan lauk tiap makan"},
                    {"key": "c", "text": "Ganti gorengan jadi kerupuk aja"},
                ],
                "answer": "b",
                "explanation": (
                    "Yang bisa kamu jalanin lama itu yang menang. Gorengan sesekali nggak "
                    "ngerusak apa-apa. Kerupuk juga digoreng, jadi itu bukan pengganti, "
                    "cuma pindah tempat."
                ),
            },
            {
                "type": "quiz",
                "key": "gorengan-4",
                "question": "Kamu makan 3 gorengan tiap hari. Langkah paling ngefek?",
                "choices": [
                    {"key": "a", "text": "Ganti 2 dari 3 jadi lauk protein yang nggak digoreng"},
                    {"key": "b", "text": "Tambah lari 20 menit"},
                    {"key": "c", "text": "Minum air lebih banyak"},
                ],
                "answer": "a",
                "explanation": (
                    "Tiga gorengan kira-kira 300 kalori tanpa protein berarti. Diganti "
                    "lauk protein, kalorinya turun dan kamu malah lebih kenyang. Lari 20 "
                    "menit cuma sekitar 150 kalori, dan itu tiap hari."
                ),
            },
        ],
    },
    {
        "slug": "serat",
        "number": 5,
        "title": "Serat & Rasa Kenyang",
        "subtitle": "Kenapa jam 3 udah laper lagi",
        "icon": "fas fa-leaf",
        "emoji": "🥬",
        "minutes": 4,
        "blocks": [
            {
                "type": "card",
                "title": "Kalori banyak, kenyang sebentar",
                "body": [
                    "Nasi, gorengan, kerupuk, minuman manis. Kalorinya gede, tapi jam 3 "
                    "kamu udah nyari makan lagi.",
                    "Yang bikin kenyang tahan lama cuma tiga: protein, serat, dan volume "
                    "makanannya. Piring yang isinya cuma karbo dan minyak nggak punya "
                    "satu pun dari ketiganya.",
                ],
            },
            {
                "type": "bars",
                "title": "Berapa banyak makanan buat 100 kalori",
                "unit": "gram makanan",
                "note": "Perkiraan, biar kelihatan bedanya aja.",
                "rows": [
                    {"label": "Sayur (bayam, kangkung)", "value": 400},
                    {"label": "Buah potong", "value": 200},
                    {"label": "Ayam bakar", "value": 110},
                    {"label": "Nasi putih", "value": 75},
                    {"label": "Bala-bala", "value": 25},
                    {"label": "Minyak", "value": 11, "muted": True},
                ],
                "caption": (
                    "Buat kalori yang sama, sayur isinya semangkok penuh dan gorengan cuma "
                    "sesuap. Perut kamu ngitung isinya, bukan kalorinya."
                ),
            },
            {
                "type": "quiz",
                "key": "serat-1",
                "question": (
                    "Kamu makan nasi + gorengan + kerupuk. Kalorinya banyak, tapi jam 3 "
                    "udah laper. Kenapa?"
                ),
                "choices": [
                    {"key": "a", "text": "Porsinya kurang banyak"},
                    {"key": "b", "text": "Minim protein dan serat, jadi kenyangnya cepat hilang"},
                    {"key": "c", "text": "Metabolisme kamu kecepetan"},
                ],
                "answer": "b",
                "explanation": (
                    "Kenyang itu bukan soal kalori doang. Protein dan serat yang bikin "
                    "rasa kenyang tahan berjam-jam. Nambah porsi nasi cuma nambah kalori "
                    "tanpa nambah tahan lapernya."
                ),
            },
            {
                "type": "card",
                "title": "Trik piring yang gampang diingat",
                "body": [
                    "Bayangin piring kamu dibagi: separuh sayur, seperempat lauk protein, "
                    "seperempat nasi.",
                    "Nggak perlu nimbang apa-apa. Di warteg pun bisa: minta sayurnya dua "
                    "macem, lauknya yang nggak digoreng, nasinya nggak usah menggunung.",
                ],
                "highlight": "Separuh sayur, seperempat protein, seperempat nasi.",
            },
            {
                "type": "quiz",
                "key": "serat-2",
                "question": "100 kalori sayur dibanding 100 kalori gorengan, di piring kelihatan?",
                "choices": [
                    {"key": "a", "text": "Sayurnya jauh lebih banyak"},
                    {"key": "b", "text": "Sama banyak"},
                    {"key": "c", "text": "Gorengannya lebih banyak"},
                ],
                "answer": "a",
                "explanation": (
                    "100 kalori sayur itu kira-kira semangkok besar. 100 kalori gorengan "
                    "kira-kira sepotong kecil. Itu kenapa orang yang banyak sayur bisa "
                    "makan kenyang tanpa kalorinya kebobolan."
                ),
            },
            {
                "type": "quiz",
                "key": "serat-3",
                "question": "Kamu mau ngurangin porsi nasi tapi takut kelaperan. Yang paling ngebantu?",
                "choices": [
                    {"key": "a", "text": "Tambah sayur dan lauk protein di piring yang sama"},
                    {"key": "b", "text": "Minum kopi biar nggak kerasa laper"},
                    {"key": "c", "text": "Makan sekali sehari aja"},
                ],
                "answer": "a",
                "explanation": (
                    "Nasi dikurangin, sayur dan protein ditambah. Piringnya tetep penuh, "
                    "kalorinya turun, dan kenyangnya malah lebih lama. Makan sekali sehari "
                    "biasanya berakhir balas dendam malemnya."
                ),
            },
            {
                "type": "quiz",
                "key": "serat-4",
                "question": "Serat paling gampang didapet dari mana, buat orang di Bandung?",
                "choices": [
                    {"key": "a", "text": "Suplemen serat di apotek"},
                    {"key": "b", "text": "Sayur di tiap makan, buah utuh, tempe, kacang"},
                    {"key": "c", "text": "Jus buah kemasan"},
                ],
                "answer": "b",
                "explanation": (
                    "Semuanya ada di warung deket rumah dan murah. Suplemen serat nggak "
                    "salah, cuma nggak perlu kalau sayur dan buahnya udah masuk. Jus "
                    "kemasan seratnya udah hilang, gulanya yang tinggal."
                ),
            },
        ],
    },
    {
        "slug": "gym",
        "number": 6,
        "title": "Kenapa Nge-Gym",
        "subtitle": "Angkat beban dan kardio, dua-duanya kepake",
        "icon": "fas fa-heart-pulse",
        "emoji": "\U0001f3cb\ufe0f",
        "minutes": 5,
        "blocks": [
            {
                "type": "card",
                "title": "Bukan pilih salah satu",
                "body": [
                    "Angkat beban dan kardio kerjanya beda, dan nggak saling gantiin. "
                    "Beban bikin otot dan tulang kuat. Kardio bikin jantung dan napas kuat.",
                    "Yang bikin badan enak dipakai sehari-hari itu dua-duanya. Naik tangga "
                    "nggak ngos-ngosan, gendong anak nggak encok, kerja seharian masih ada "
                    "tenaga.",
                ],
            },
            {
                "type": "card",
                "title": "Yang berubah di dalam badan",
                "body": [
                    "Kardio: jantung mompa lebih efisien, denyut waktu istirahat turun, "
                    "tekanan darah lebih terkontrol. Napas kamu jadi punya cadangan.",
                    "Angkat beban: ototnya nambah, dan otot itu tempat gula darah dipakai. "
                    "Makanya latihan beban bikin gula darah lebih stabil, dan itu penting "
                    "banget di sini karena diabetes tipe 2 udah umum banget. Tulang juga "
                    "ikut lebih padat, punggung dan lutut lebih aman.",
                ],
                "highlight": "Otot itu tempat gula darah dipakai. Nambah otot = badan lebih tahan diabetes.",
            },
            {
                "type": "card",
                "title": "Yang kerasa di luar",
                "body": [
                    "Tidur lebih gampang, stres lebih ketahan, tenaga harian naik. Banyak "
                    "member cerita ini yang paling kerasa, bukan angka di timbangan.",
                    "Dan buat yang mau turun berat badan: latihan beban yang bikin yang "
                    "hilang itu lemaknya, bukan ototnya. Itu bedanya turun berat badan "
                    "terus kelihatan kencang, sama turun berat badan tapi kelihatan lemes.",
                ],
            },
            {
                "type": "verdicts",
                "title": "Kata orang soal gym",
                "rows": [
                    {
                        "claim": "Kardio doang cukup buat kurus",
                        "is_true": False,
                        "note": "Berat bisa turun, tapi otot ikut kebawa. Badan gampang balik lagi.",
                    },
                    {
                        "claim": "Angkat beban cuma buat yang mau badan gede",
                        "is_true": False,
                        "note": "Manfaat utamanya kekuatan harian, tulang, dan gula darah. Gede itu proyek sendiri.",
                    },
                    {
                        "claim": "Harus 2 jam tiap hari baru ngefek",
                        "is_true": False,
                        "note": "2-3x seminggu, 45-60 menit, udah dapet sebagian besar manfaatnya.",
                    },
                    {
                        "claim": "Umur 40+ udah telat mulai",
                        "is_true": False,
                        "note": "Justru paling untung. Otot dan tulang turun sendiri kalau nggak dilatih.",
                    },
                    {
                        "claim": "Kalau nggak keringetan berarti nggak ngefek",
                        "is_true": False,
                        "note": "Angkat beban sering nggak bikin basah, tapi paling ngefek buat otot.",
                    },
                    {
                        "claim": "Jalan kaki itung olahraga",
                        "is_true": True,
                        "note": "Kalau cukup cepat dan rutin, iya. Ini yang paling gampang dijalanin.",
                    },
                ],
            },
            {
                "type": "quiz",
                "key": "gym-1",
                "question": "Kamu cuma kardio tiap hari, nggak pernah angkat beban. Waktu berat badan turun...",
                "choices": [
                    {"key": "a", "text": "Yang hilang pasti lemak semua"},
                    {"key": "b", "text": "Otot ikut kebawa, jadi badan kelihatan lemes dan gampang balik"},
                    {"key": "c", "text": "Otot otomatis nambah"},
                ],
                "answer": "b",
                "explanation": (
                    "Tanpa latihan beban, badan nggak punya alasan buat nahan ototnya. "
                    "Ototnya berkurang, kebutuhan kalorinya juga turun, dan itu yang bikin "
                    "berat gampang balik. Tambah 2x latihan beban seminggu, ceritanya beda."
                ),
            },
            {
                "type": "quiz",
                "key": "gym-2",
                "question": "Kenapa latihan beban bagus buat gula darah?",
                "choices": [
                    {"key": "a", "text": "Karena bikin keringetan banyak"},
                    {"key": "b", "text": "Otot itu tempat gula darah dipakai, ototnya nambah, gulanya lebih terkontrol"},
                    {"key": "c", "text": "Nggak ada hubungannya sama gula darah"},
                ],
                "answer": "b",
                "explanation": (
                    "Otot itu pelanggan terbesar gula darah kamu. Makin banyak dan makin "
                    "sering dipakai, makin gampang badan ngatur gulanya. Buat orang dengan "
                    "riwayat diabetes di keluarga, ini salah satu alasan terkuat buat "
                    "angkat beban."
                ),
            },
            {
                "type": "quiz",
                "key": "gym-3",
                "question": "Patokan seminggu yang masuk akal buat orang kerja?",
                "choices": [
                    {"key": "a", "text": "2 jam tiap hari, nggak boleh bolong"},
                    {"key": "b", "text": "2-3x latihan beban + jalan cepat 30 menit beberapa hari"},
                    {"key": "c", "text": "1x seminggu tapi 4 jam sekalian"},
                ],
                "answer": "b",
                "explanation": (
                    "Anjuran umumnya kira-kira 150 menit kardio sedang seminggu plus 2 sesi "
                    "latihan beban. Dibagi jadi porsi kecil malah lebih gampang dijalanin, "
                    "dan yang rutin itu yang ngasih hasil."
                ),
            },
            {
                "type": "quiz",
                "key": "gym-4",
                "question": "Umur 45, belum pernah latihan beban seumur hidup. Sebaiknya?",
                "choices": [
                    {"key": "a", "text": "Udah telat, cukup jalan kaki aja"},
                    {"key": "b", "text": "Justru paling untung mulai sekarang, mulai dari beban ringan"},
                    {"key": "c", "text": "Tunggu berat badan turun dulu, baru angkat beban"},
                ],
                "answer": "b",
                "explanation": (
                    "Dari umur 30-an, otot dan tulang turun sendiri kalau nggak dilatih. "
                    "Jadi yang paling banyak dapet manfaat justru yang mulai belakangan. "
                    "Mulai dari beban ringan dan gerakan yang bener, nggak usah buru-buru."
                ),
            },
        ],
    },
    {
        "slug": "otot",
        "number": 7,
        "title": "Otot",
        "subtitle": "Apa yang beneran bikin otot tumbuh",
        "icon": "fas fa-dumbbell",
        "emoji": "💪",
        "minutes": 5,
        "blocks": [
            {
                "type": "card",
                "title": "Cuma tiga bahannya",
                "body": [
                    "Otot tumbuh dari tiga hal: latihan yang makin berat, protein yang "
                    "cukup, dan tidur. Itu aja.",
                    "Suplemen bukan salah satunya. Suplemen cuma jalan pintas biar protein "
                    "gampang masuk, dan itu pun bisa diganti telur dan tempe.",
                ],
                "highlight": "Latihan makin berat + protein cukup + tidur cukup. Sisanya bonus.",
            },
            {
                "type": "card",
                "title": "Naik dikit-dikit, tapi naik",
                "body": [
                    "Badan cuma berubah kalau dipaksa. Kalau beban dan repetisi kamu sama "
                    "terus selama 4 bulan, badan udah nyaman dan nggak punya alasan buat "
                    "nambah otot.",
                    "Nggak harus loncat jauh. Tambah 1 repetisi, atau naik beban paling "
                    "kecil, tiap satu dua minggu. Catet di HP biar kelihatan naiknya.",
                ],
            },
            {
                "type": "quiz",
                "key": "otot-1",
                "question": "Kamu latihan 3x seminggu, beban sama terus selama 4 bulan. Kira-kira?",
                "choices": [
                    {"key": "a", "text": "Otot terus nambah, yang penting rutin"},
                    {"key": "b", "text": "Badan udah nyaman, perlu naik beban atau repetisi"},
                    {"key": "c", "text": "Harus ganti olahraga total"},
                ],
                "answer": "b",
                "explanation": (
                    "Rutin itu syarat, bukan tujuan. Yang bikin otot nambah itu bebannya "
                    "makin berat dari waktu ke waktu. Nggak perlu ganti olahraga, cukup "
                    "naikin sedikit."
                ),
            },
            {
                "type": "card",
                "title": "Tidur itu bagian dari latihan",
                "body": [
                    "Otot dibangun waktu kamu tidur, bukan waktu kamu latihan. Latihan cuma "
                    "ngasih sinyal.",
                    "Tidur 4-5 jam bikin pemulihan jelek, tenaga di gym turun, dan rasa "
                    "laper naik. Banyak orang yang 'programnya gagal' sebenernya cuma "
                    "kurang tidur.",
                ],
            },
            {
                "type": "verdicts",
                "title": "Suplemen: mana yang ada buktinya",
                "note": "Buat orang sehat yang latihan biasa, bukan atlet.",
                "rows": [
                    {
                        "claim": "Kreatin",
                        "is_true": True,
                        "note": "Paling terbukti dan murah. Kira-kira 3-5 gram sehari, kapan aja.",
                    },
                    {
                        "claim": "Whey protein",
                        "is_true": True,
                        "note": "Beneran protein, cuma praktis. Bukan wajib kalau makanmu udah cukup.",
                    },
                    {
                        "claim": "Fat burner",
                        "is_true": False,
                        "note": "Efeknya kecil banget, harganya nggak. Yang ngebakar lemak itu makanmu.",
                    },
                    {
                        "claim": "BCAA",
                        "is_true": False,
                        "note": "Nggak nambah apa-apa kalau protein harianmu udah cukup.",
                    },
                    {
                        "claim": "Susu penggemuk / penambah massa",
                        "is_true": False,
                        "note": "Isinya banyak gula. Kalau mau nambah berat, nambah makanan aja.",
                    },
                ],
            },
            {
                "type": "quiz",
                "key": "otot-2",
                "question": "Suplemen yang paling terbukti buat kekuatan dan otot?",
                "choices": [
                    {"key": "a", "text": "Fat burner"},
                    {"key": "b", "text": "Kreatin"},
                    {"key": "c", "text": "BCAA"},
                ],
                "answer": "b",
                "explanation": (
                    "Kreatin itu suplemen paling banyak diteliti dan salah satu yang "
                    "paling murah. Tetep nomor dua sesudah latihan dan makan, tapi kalau "
                    "kamu mau beli satu, ini yang masuk akal."
                ),
            },
            {
                "type": "quiz",
                "key": "otot-3",
                "question": "Buat cewek, latihan beban bikin badan...",
                "choices": [
                    {"key": "a", "text": "Langsung gede kayak binaragawan"},
                    {"key": "b", "text": "Lebih padat dan kencang; gede butuh tahunan dan makan banyak"},
                    {"key": "c", "text": "Nggak ngefek apa-apa"},
                ],
                "answer": "b",
                "explanation": (
                    "Badan gede itu proyek bertahun-tahun dengan makan banyak dan latihan "
                    "berat. Latihan beban biasa bikin badan lebih padat dan kuat, dan itu "
                    "yang orang maksud waktu bilang 'kencang'."
                ),
            },
            {
                "type": "quiz",
                "key": "otot-4",
                "question": "Tidur 4-5 jam tiap malam, pengaruhnya ke otot?",
                "choices": [
                    {"key": "a", "text": "Nggak ada, yang penting latihan"},
                    {"key": "b", "text": "Pemulihan jelek, tenaga turun, laper naik"},
                    {"key": "c", "text": "Bikin otot lebih cepat tumbuh"},
                ],
                "answer": "b",
                "explanation": (
                    "Kurang tidur bikin badanmu susah mulih, angkatanmu turun, dan nafsu "
                    "makanmu naik. Nambah jam tidur sering lebih ngefek daripada nambah "
                    "suplemen."
                ),
            },
        ],
    },
    {
        "slug": "mitos",
        "number": 8,
        "title": "Mitos Lokal",
        "subtitle": "Yang sering kedengeran, tapi nggak bener",
        "icon": "fas fa-ghost",
        "emoji": "👻",
        "minutes": 4,
        "blocks": [
            {
                "type": "card",
                "title": "Kenapa mitos ini nempel",
                "body": [
                    "Hampir semua mitos diet punya satu kesamaan: ada yang kelihatan "
                    "berhasil di awal. Timbangan turun 2 kilo dalam 3 hari, jadi kayaknya "
                    "bener.",
                    "Yang turun itu air dan isi perut, bukan lemak. Begitu makan normal "
                    "lagi, angkanya balik, dan orang nyalahin dirinya sendiri.",
                ],
            },
            {
                "type": "verdicts",
                "title": "Bener nggak?",
                "rows": [
                    {
                        "claim": "Makan malam bikin gendut",
                        "is_true": False,
                        "note": "Yang nentuin total sehari, bukan jam makannya.",
                    },
                    {
                        "claim": "Nasi dan karbo itu jahat",
                        "is_true": False,
                        "note": "Porsinya yang bikin masalah, bukan nasinya.",
                    },
                    {
                        "claim": "Keringetan banyak berarti lemak kebakar banyak",
                        "is_true": False,
                        "note": "Keringat itu cara badan mendinginkan diri. Beratnya balik habis minum.",
                    },
                    {
                        "claim": "Sit-up bikin perut rata",
                        "is_true": False,
                        "note": "Perut rata datang dari makan dan kalori, bukan dari gerakan perut.",
                    },
                    {
                        "claim": "Teh detox bikin turun lemak",
                        "is_true": False,
                        "note": "Yang keluar air dan isi perut. Hati dan ginjal kamu udah kerja gratis.",
                    },
                    {
                        "claim": "Kental manis itu susu",
                        "is_true": False,
                        "note": "Kira-kira separuhnya gula, proteinnya tipis banget.",
                    },
                ],
            },
            {
                "type": "quiz",
                "key": "mitos-1",
                "question": "Kamu makan nasi jam 9 malam. Yang terjadi?",
                "choices": [
                    {"key": "a", "text": "Otomatis jadi lemak karena kemaleman"},
                    {"key": "b", "text": "Sama aja, yang penting total kalori seharian"},
                    {"key": "c", "text": "Naik 1 kilo besok pagi"},
                ],
                "answer": "b",
                "explanation": (
                    "Badan nggak punya jam yang bilang 'lewat jam 8 disimpen jadi lemak'. "
                    "Kalau makan malem sering bikin kebobolan, itu biasanya karena "
                    "porsinya besar atau kamu skip makan siang, bukan karena jamnya."
                ),
            },
            {
                "type": "quiz",
                "key": "mitos-2",
                "question": "Habis olahraga keringetan basah semua. Itu artinya?",
                "choices": [
                    {"key": "a", "text": "Lemaknya kebakar banyak"},
                    {"key": "b", "text": "Badan lagi mendinginkan diri; beratnya balik habis minum"},
                    {"key": "c", "text": "Berat badan turun permanen"},
                ],
                "answer": "b",
                "explanation": (
                    "Keringat itu air. Latihan angkat beban yang bikin kamu nggak "
                    "keringetan bisa lebih ngebentuk badan daripada sauna yang bikin basah "
                    "kuyup."
                ),
            },
            {
                "type": "quiz",
                "key": "mitos-3",
                "question": "Mau perut lebih rata. Paling ngefek?",
                "choices": [
                    {"key": "a", "text": "Sit-up 100x tiap hari"},
                    {"key": "b", "text": "Kalori sedikit di bawah kebutuhan + protein + latihan seluruh badan"},
                    {"key": "c", "text": "Pakai korset atau sabuk pemanas"},
                ],
                "answer": "b",
                "explanation": (
                    "Nggak ada gerakan yang bisa milih lemak di satu tempat buat dibakar. "
                    "Sit-up nguatin otot perut, tapi yang bikin kelihatan itu lapisan "
                    "lemaknya berkurang, dan itu dari makan."
                ),
            },
            {
                "type": "quiz",
                "key": "mitos-4",
                "question": "Teh pelangsing bikin timbangan turun 2 kilo dalam 3 hari. Itu kemungkinan besar?",
                "choices": [
                    {"key": "a", "text": "Lemak, berarti ampuh"},
                    {"key": "b", "text": "Air dan isi perut"},
                    {"key": "c", "text": "Otot"},
                ],
                "answer": "b",
                "explanation": (
                    "Turun 2 kilo lemak dalam 3 hari itu perlu defisit belasan ribu "
                    "kalori, nggak mungkin. Yang turun air dan isi perut, dan itu balik "
                    "dalam sehari."
                ),
            },
        ],
    },
    {
        "slug": "kemasan",
        "number": 9,
        "title": "Makanan Kemasan",
        "subtitle": "Baca labelnya, jangan iklannya",
        "icon": "fas fa-cookie-bite",
        "emoji": "🍪",
        "minutes": 5,
        "blocks": [
            {
                "type": "card",
                "title": "Kemasan nggak otomatis jahat",
                "body": [
                    "Susu UHT, tuna kaleng, telur, oat, tempe, kacang. Semuanya kemasan, "
                    "semuanya oke.",
                    "Yang bikin masalah itu makanan yang gulanya banyak, minyaknya banyak, "
                    "proteinnya nol, dan rasanya dibikin supaya kamu susah berhenti. Ciri "
                    "gampangnya: bahannya panjang dan banyak yang nggak pernah ada di dapur.",
                ],
            },
            {
                "type": "card",
                "title": "Baca label dalam 10 detik",
                "body": [
                    "Satu: cek 'per sajian' atau 'per kemasan'. Satu bungkus sering dihitung "
                    "2 sajian, jadi kalorinya dua kali dari yang kamu baca.",
                    "Dua: lihat gulanya per sajian. Tiga: lihat proteinnya. Kalau gulanya "
                    "dua digit dan proteinnya nol, itu jajanan, bukan makanan.",
                ],
                "highlight": "Cek sajian dulu, baru gula, baru protein. Itu udah 90% dari baca label.",
            },
            {
                "type": "bars",
                "title": "Kira-kira gula per kemasan",
                "unit": "gram gula",
                "note": "Perkiraan, beda merek beda isi. Cek labelnya sendiri ya.",
                "rows": [
                    {"label": "Soda 330ml", "value": 35},
                    {"label": "Teh kemasan 350ml", "value": 25},
                    {"label": "Kental manis 2 sdm", "value": 13},
                    {"label": "Sereal manis 1 saji", "value": 12},
                    {"label": "Biskuit 1 bungkus kecil", "value": 10},
                    {"label": "Batas sehari (anjuran)", "value": 50, "muted": True},
                ],
                "caption": (
                    "Baris terakhir itu batas anjuran sehari, kira-kira 50 gram atau 4 "
                    "sendok makan. Satu soda plus satu teh kemasan udah lebih dari separuhnya."
                ),
            },
            {
                "type": "quiz",
                "key": "kemasan-1",
                "question": (
                    "Label bilang 'per sajian 120 kalori', dan satu bungkus isinya 2 sajian. "
                    "Kamu habisin sebungkus. Kalorinya?"
                ),
                "choices": [
                    {"key": "a", "text": "120"},
                    {"key": "b", "text": "240"},
                    {"key": "c", "text": "60"},
                ],
                "answer": "b",
                "explanation": (
                    "Ini jebakan label paling sering. Angka yang dipajang gede itu per "
                    "sajian, dan hampir nggak ada orang yang makan setengah bungkus lalu "
                    "berhenti. Selalu cek jumlah sajiannya dulu."
                ),
            },
            {
                "type": "verdicts",
                "title": "Klaim di bungkus",
                "rows": [
                    {
                        "claim": "\"Rendah lemak\"",
                        "is_true": False,
                        "note": "Lemaknya dikurangin, gulanya sering ditambah biar tetep enak.",
                    },
                    {
                        "claim": "\"Tanpa gula tambahan\"",
                        "is_true": False,
                        "note": "Bisa tetep tinggi kalori dari gula alami atau lemaknya.",
                    },
                    {
                        "claim": "\"Rasa buah\"",
                        "is_true": False,
                        "note": "Biasanya perisa. Buah aslinya sering nggak sampai 1%.",
                    },
                    {
                        "claim": "\"Mengandung susu\"",
                        "is_true": False,
                        "note": "Mengandung, bukan berarti banyak. Cek proteinnya di label.",
                    },
                    {
                        "claim": "Ada BPOM dan halal",
                        "is_true": True,
                        "note": "Artinya aman dan halal, bukan berarti sehat atau rendah gula.",
                    },
                ],
            },
            {
                "type": "quiz",
                "key": "kemasan-2",
                "question": "Produk yang ditulis 'rendah lemak' biasanya...",
                "choices": [
                    {"key": "a", "text": "Otomatis rendah kalori"},
                    {"key": "b", "text": "Gulanya sering ditambah biar rasanya tetep enak"},
                    {"key": "c", "text": "Selalu lebih sehat dari versi biasa"},
                ],
                "answer": "b",
                "explanation": (
                    "Lemak itu yang bikin makanan enak. Begitu dikurangin, pabrik perlu "
                    "ganti sesuatu, dan biasanya gula. Bandingin labelnya sebelah-sebelahan, "
                    "sering kalorinya mirip."
                ),
            },
            {
                "type": "quiz",
                "key": "kemasan-3",
                "question": "Camilan harian yang paling masuk akal?",
                "choices": [
                    {"key": "a", "text": "Biskuit manis sebungkus"},
                    {"key": "b", "text": "Telur rebus, buah, atau yogurt tawar"},
                    {"key": "c", "text": "Minuman kemasan rasa buah"},
                ],
                "answer": "b",
                "explanation": (
                    "Ketiganya gampang dibeli dan ada proteinnya atau seratnya, jadi "
                    "kenyangnya kebawa. Biskuit dan minuman rasa buah kalorinya masuk tanpa "
                    "bikin kenyang, dan malah bikin pengen lagi."
                ),
            },
            {
                "type": "quiz",
                "key": "kemasan-4",
                "question": "Jadi makanan kemasan itu...",
                "choices": [
                    {"key": "a", "text": "Semuanya jahat, hindari total"},
                    {"key": "b", "text": "Tergantung isinya: susu UHT dan tuna kaleng oke, yang manis dan nol protein yang masalah"},
                    {"key": "c", "text": "Aman semua asal ada label BPOM"},
                ],
                "answer": "b",
                "explanation": (
                    "Menghindari semua kemasan itu nggak realistis dan nggak perlu. Yang "
                    "perlu kamu bedain: mana yang ngasih protein dan serat, mana yang cuma "
                    "ngasih gula, minyak, dan rasa."
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
    """The band a member is in. Reads backwards, so the first match wins."""
    done = max(0, chapters_done)
    for level in reversed(LEVELS):
        if done >= level["min"]:
            return level["name"]
    return LEVELS[0]["name"]


def level_chips():
    """The whole ladder, labelled as ranges: "0 bab", "1-2 bab", "3-4 bab"."""
    chips = []
    for index, level in enumerate(LEVELS):
        low = level["min"]
        high = LEVELS[index + 1]["min"] - 1 if index + 1 < len(LEVELS) else None
        label = f"{low} bab" if high is None or high <= low else f"{low}-{high} bab"
        chips.append({"label": label, "name": level["name"]})
    return chips


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
