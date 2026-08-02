"""The 100 daily quiz questions, seeded into the database by a migration.

Format is deliberately compact so a human can review a hundred of them without
losing the will to live:

    ("code", "question", ["choice a", "choice b", "choice c"], answer_index,
     "explanation")

`_build` turns each row into the shape the model stores: choices keyed a/b/c and
the answer as a letter. Position comes from the order in this list, and that
order is what decides which question lands on which day.

Rules for editing:

- **A `code` is permanent.** It is the key the seeding migration matches on and
  what every recorded answer points at, so renaming one orphans its history.
  Reorder freely, rename never.
- **Adding questions**: append to the end and add a migration that calls the same
  sync helper. Appending changes which day a question lands on, which is
  harmless: the point is that there is one waiting every morning.
- **Editing wording after launch**: change it in `/admin`. Editing here alone does
  nothing to a database that has already been seeded.
- Every number is an estimate and says so. Portions vary by warung.
"""

from .shuffle import place_answer

RAW = [
    # --- kalori dan berat badan -------------------------------------------
    (
        "dq-001",
        "Mana yang paling padat kalori per gram?",
        ["Minyak", "Gula", "Protein"],
        0,
        "Minyak 9 kalori per gram, gula dan protein cuma 4. Makanya minyak paling gampang bikin kalori naik tanpa kelihatan.",
    ),
    (
        "dq-002",
        "Buat nurunin 1 kg lemak badan, kira-kira butuh kekurangan kalori sebanyak?",
        ["1.000 kalori", "7.700 kalori", "50.000 kalori"],
        1,
        "Kira-kira 7.700. Itu kenapa turun setengah kilo seminggu udah bagus, dan kenapa 'turun 5 kg dalam 3 hari' itu air, bukan lemak.",
    ),
    (
        "dq-003",
        "Timbangan naik 1 kg dari kemarin. Paling mungkin itu?",
        ["Lemak baru", "Air dan isi perut", "Otot baru"],
        1,
        "Lemak nggak bisa nambah 1 kg dalam sehari, itu butuh kelebihan 7.700 kalori. Yang naik air, garam, dan isi perut.",
    ),
    (
        "dq-004",
        "Turun berat badan yang realistis dan aman itu kira-kira?",
        ["0,3 sampai 0,7 kg per minggu", "2 sampai 3 kg per minggu", "5 kg per minggu"],
        0,
        "Lebih cepat dari itu biasanya air dan otot yang ikut hilang, dan hampir selalu balik lagi.",
    ),
    (
        "dq-005",
        "Nasi putih 1 centong (kira-kira 100 gram) itu berapa kalori?",
        ["Sekitar 50", "Sekitar 130", "Sekitar 400"],
        1,
        "Sekitar 130. Nasi sering disalahin padahal porsinya yang perlu diatur, bukan nasinya yang jahat.",
    ),
    (
        "dq-006",
        "5 keping kerupuk kira-kira setara?",
        ["Sekitar 30 kalori", "Sekitar 150 kalori", "Sekitar 500 kalori"],
        1,
        "Sekitar 150, karena kerupuk digoreng dan nyerep minyak. Kenyangnya nol.",
    ),
    (
        "dq-007",
        "Kenapa kalori makanan di luar susah dikira-kira?",
        [
            "Porsinya selalu kecil",
            "Minyak, gula dan santannya nggak kelihatan",
            "Bahannya lebih murah",
        ],
        1,
        "Yang bikin bengkak biasanya yang nggak kelihatan: minyak masak, gula di bumbu dan minuman, santan, dan saus.",
    ),
    (
        "dq-008",
        "Diet yang paling berhasil dalam jangka panjang biasanya yang?",
        [
            "Paling ketat dan paling cepat",
            "Bisa kamu jalanin bertahun-tahun",
            "Tanpa karbohidrat sama sekali",
        ],
        1,
        "Aturan paling ketat menang di minggu pertama dan kalah di bulan ketiga. Yang bertahan itu yang nggak bikin kamu tersiksa.",
    ),
    (
        "dq-009",
        "Kalau kalori yang masuk sama dengan yang kepakai, berat badan?",
        ["Naik pelan", "Stabil", "Turun pelan"],
        1,
        "Stabil. Itu juga kenapa berat bisa mandek walaupun kamu ngerasa udah ngurangin makan.",
    ),
    (
        "dq-010",
        "Makan lebih pelan bisa ngebantu ngurangin porsi karena?",
        [
            "Kalorinya berkurang kalau dikunyah lama",
            "Rasa kenyang butuh kira-kira 20 menit buat kekirim ke otak",
            "Metabolisme naik",
        ],
        1,
        "Sinyal kenyang datang telat. Makan cepat berarti kamu udah nambah sebelum badan sempat bilang cukup.",
    ),
    (
        "dq-011",
        "Angka 'kalori terbakar' di alat kardio biasanya?",
        ["Pas banget", "Sering lebih tinggi dari yang sebenarnya", "Selalu lebih rendah"],
        1,
        "Alatnya nggak tahu berat, umur dan efisiensi gerak kamu. Jangan dipakai buat 'ngebayar' makanan.",
    ),
    (
        "dq-012",
        "Mau turun berat badan tanpa laper terus. Yang paling ngebantu?",
        [
            "Protein dan sayur di tiap makan",
            "Makan sekali sehari",
            "Ganti nasi putih ke nasi merah",
        ],
        0,
        "Protein dan serat yang bikin kenyang tahan lama. Makan sekali sehari biasanya berakhir balas dendam malamnya.",
    ),
    # --- protein ----------------------------------------------------------
    (
        "dq-013",
        "1 telur ukuran sedang kira-kira ngasih protein?",
        ["2 gram", "6 sampai 7 gram", "20 gram"],
        1,
        "Sekitar 6 sampai 7 gram, dengan harga paling murah di pasar. Nambah 1 telur ke sarapan itu langkah termudah.",
    ),
    (
        "dq-014",
        "100 gram tempe kira-kira ngasih protein?",
        ["5 gram", "19 gram", "40 gram"],
        1,
        "Sekitar 19 gram. Nggak ada yang ngalahin tempe kalau dihitung protein per rupiah.",
    ),
    (
        "dq-015",
        "100 gram ayam dada kira-kira ngasih protein?",
        ["8 gram", "23 gram", "50 gram"],
        1,
        "Sekitar 23 gram. Sepotong ayam sedang udah nutup seperempat kebutuhan harian orang 60 kg.",
    ),
    (
        "dq-016",
        "Buat yang latihan, patokan protein harian per kilo berat badan?",
        ["0,5 gram", "1,6 gram", "5 gram"],
        1,
        "Sekitar 1,6 gram per kilo. Berat 60 kg berarti kira-kira 95 gram sehari.",
    ),
    (
        "dq-017",
        "Per kalori yang sama, mana yang paling bikin kenyang?",
        ["Protein", "Lemak", "Gula"],
        0,
        "Protein menang jauh. Itu kenapa piring yang ada lauknya bikin kamu tahan sampai sore.",
    ),
    (
        "dq-018",
        "Kalau protein dari makanan udah cukup, whey protein itu?",
        ["Wajib", "Opsional, cuma praktis", "Berbahaya"],
        1,
        "Whey cuma protein yang dibikin gampang diminum. Berguna kalau susah makan, tapi bukan syarat.",
    ),
    (
        "dq-019",
        "Protein dari tempe, tahu dan kacang buat bikin otot?",
        [
            "Nggak berguna",
            "Tetep ngebantu, apalagi kalau sumbernya macam-macam",
            "Lebih bagus dari hewani",
        ],
        1,
        "Nabati tetep dihitung. Campur macam-macam sumber dan total hariannya cukup, ototnya kebentuk.",
    ),
    (
        "dq-020",
        "Waktu makan protein yang paling penting?",
        [
            "Wajib dalam 30 menit setelah latihan",
            "Total seharian yang paling penting",
            "Cuma sebelum tidur",
        ],
        1,
        "Jendela 30 menit itu mitos lama. Yang menentukan total protein sehari, bukan menit-menitnya.",
    ),
    (
        "dq-021",
        "Susu cair 250 ml kira-kira ngasih protein?",
        ["2 gram", "8 gram", "25 gram"],
        1,
        "Sekitar 8 gram. Ganti minuman manis jadi susu, sekalian dapet protein.",
    ),
    (
        "dq-022",
        "Ikan kembung dibanding ayam dada, proteinnya?",
        ["Jauh lebih rendah", "Mirip", "Hampir nol"],
        1,
        "Mirip, sekitar 21 lawan 23 gram per 100 gram. Ikan kembung juga murah dan ada omega-3 nya.",
    ),
    (
        "dq-023",
        "Lauk kamu tiap makan cuma sepotong kecil. Cara termudah nambah protein?",
        ["Tambah 1 telur", "Tambah nasi", "Tambah kerupuk"],
        0,
        "Telur paling murah, paling gampang, dan ada di mana-mana. Nasi dan kerupuk nggak nambah protein.",
    ),
    (
        "dq-024",
        "Buat orang sehat, makan protein sekitar 1,6 sampai 2 gram per kilo itu?",
        [
            "Bikin ginjal rusak",
            "Nggak ada bukti bikin masalah",
            "Cuma aman kalau dari tumbuhan",
        ],
        1,
        "Buat orang sehat nggak ada buktinya. Kalau kamu punya penyakit ginjal, itu beda cerita, tanya dokter.",
    ),
    # --- gula dan minuman -------------------------------------------------
    (
        "dq-025",
        "Es teh manis 1 gelas warung kira-kira ada gula sebanyak?",
        ["1 sendok teh", "5 sampai 7 sendok teh", "20 sendok teh"],
        1,
        "Kira-kira 5 sampai 7 sendok teh, sekitar 110 kalori yang nggak bikin kenyang sama sekali.",
    ),
    (
        "dq-026",
        "Batas gula tambahan sehari yang biasa dianjurkan?",
        ["Sekitar 4 sendok makan (50 gram)", "Sekitar 15 sendok makan", "Nggak ada batas"],
        0,
        "Sekitar 50 gram sehari. Satu botol soda plus satu teh kemasan udah lewat separuhnya.",
    ),
    (
        "dq-027",
        "Susu kental manis dibanding susu cair?",
        [
            "Proteinnya lebih tinggi",
            "Proteinnya jauh lebih sedikit, gulanya jauh lebih banyak",
            "Sama saja",
        ],
        1,
        "Kental manis kira-kira separuhnya gula. Namanya susu, isinya lebih dekat ke sirup.",
    ),
    (
        "dq-028",
        "Minuman soda 'zero sugar' buat yang mau turun berat badan?",
        ["Lebih bikin gendut", "Jauh lebih baik dari yang bergula", "Sama saja"],
        1,
        "Kalorinya hampir nol. Bukan air putih, tapi jelas lebih baik daripada 35 gram gula per kaleng.",
    ),
    (
        "dq-029",
        "Kopi hitam tanpa gula kalorinya kira-kira?",
        ["Hampir nol", "100", "250"],
        0,
        "Hampir nol. Yang bikin kopi jadi 250 kalori itu gula aren, krimer dan kental manisnya.",
    ),
    (
        "dq-030",
        "Boba milk tea 500 ml kira-kira?",
        ["100 kalori", "350 sampai 450 kalori", "800 kalori"],
        1,
        "Sekitar 350 sampai 450, setara sepiring nasi dengan lauk. Bedanya, ini nggak bikin kenyang.",
    ),
    (
        "dq-031",
        "Jus buah tanpa gula tambahan dibanding buah utuh?",
        ["Buah utuh lebih bikin kenyang", "Jus lebih bikin kenyang", "Sama"],
        0,
        "Serat di buah utuh masih utuh, jadi lebih ngenyangin dan gulanya masuk lebih pelan.",
    ),
    (
        "dq-032",
        "Minum air putih sebelum makan bisa ngebantu karena?",
        ["Bikin lemak larut", "Bikin lebih cepat kenyang, porsinya jadi terkontrol", "Nggak ada efeknya"],
        1,
        "Sederhana tapi lumayan ngebantu, dan gratis.",
    ),
    (
        "dq-033",
        "Kebutuhan cairan orang dewasa sehari kira-kira?",
        ["Setengah liter", "2 sampai 3 liter tergantung aktivitas dan cuaca", "8 liter"],
        1,
        "Di Bandung yang lembap dan kalau kamu latihan, ambil yang atas. Warna pipis yang gelap itu tanda kurang.",
    ),
    (
        "dq-034",
        "Rasa haus itu tanda?",
        ["Kamu udah mulai kurang cairan", "Badan kelebihan air", "Kamu lapar"],
        0,
        "Haus itu sinyal yang datangnya agak telat. Jangan nunggu haus baru minum, apalagi waktu latihan.",
    ),
    # --- gorengan, minyak, cara masak -------------------------------------
    (
        "dq-035",
        "1 sendok makan minyak goreng kira-kira?",
        ["40 kalori", "120 kalori", "300 kalori"],
        1,
        "Sekitar 120 kalori, dan itu cuma satu sendok yang kamu nggak lihat masuk ke penggorengan.",
    ),
    (
        "dq-036",
        "Gorengan nyerep minyak paling banyak kalau minyaknya?",
        ["Kurang panas", "Sangat panas", "Nggak ngaruh"],
        0,
        "Minyak kurang panas bikin makanan kelamaan di dalam dan nyerep lebih banyak. Yang panas cepat bikin lapisan luar.",
    ),
    (
        "dq-037",
        "Sepotong ayam goreng tepung dibanding ayam bakar, bedanya kira-kira?",
        ["10 kalori", "150 kalori", "1.000 kalori"],
        1,
        "Sekitar 150 kalori, dan proteinnya sama. Kamu bayar 150 kalori cuma buat cara masaknya.",
    ),
    (
        "dq-038",
        "Cara masak paling hemat kalori?",
        ["Goreng banyak minyak", "Kukus, rebus, bakar, atau tumis sedikit minyak", "Sama semua"],
        1,
        "Bahan yang sama bisa beda ratusan kalori cuma dari cara masaknya.",
    ),
    (
        "dq-039",
        "Kerupuk itu?",
        ["Camilan bebas kalori", "Digoreng juga, jadi padat kalori", "Sumber protein"],
        1,
        "Kerupuk itu gorengan yang nggak dianggap gorengan. Kalorinya masuk, kenyangnya nggak.",
    ),
    (
        "dq-040",
        "Minyak kelapa yang dibilang 'lemak sehat' itu?",
        ["Bebas kalori", "Tetep 9 kalori per gram", "Lebih rendah kalori dari minyak lain"],
        1,
        "Sehat atau nggak, semua minyak 9 kalori per gram. Jumlahnya tetep dihitung.",
    ),
    (
        "dq-041",
        "Santan kental 100 ml kira-kira?",
        ["30 kalori", "Sekitar 200 kalori", "800 kalori"],
        1,
        "Sekitar 200. Bukan haram, cuma perlu diinget kalau kuahnya diminum sampai habis.",
    ),
    (
        "dq-042",
        "Kamu tetep suka gorengan. Yang paling masuk akal?",
        [
            "Berhenti total",
            "Jadiin camilan kadang-kadang, bukan lauk tiap makan",
            "Ganti semua jadi kerupuk",
        ],
        1,
        "Aturan yang bisa dijalanin menang. Kerupuk juga digoreng, jadi itu cuma pindah tempat.",
    ),
    (
        "dq-043",
        "Lemak di makanan itu?",
        ["Nggak perlu sama sekali", "Perlu, buat hormon dan nyerap vitamin tertentu", "Cuma buat rasa"],
        1,
        "Diet tanpa lemak sama sekali itu ide buruk. Yang perlu diatur jumlahnya, bukan dihapus.",
    ),
    (
        "dq-044",
        "1 sendok makan mayones kira-kira?",
        ["20 kalori", "Sekitar 90 kalori", "300 kalori"],
        1,
        "Sekitar 90, hampir semuanya minyak. Saus dan mayo itu tempat kalori sembunyi paling sering.",
    ),
    # --- sayur, serat, rasa kenyang ---------------------------------------
    (
        "dq-045",
        "Serat bikin kenyang karena?",
        ["Kalorinya tinggi", "Nambah volume dan memperlambat pencernaan", "Bikin haus"],
        1,
        "Isi perutnya banyak, kalorinya sedikit, dan turunnya pelan. Itu kombinasi yang bikin tahan lapar.",
    ),
    (
        "dq-046",
        "Sayur yang dimasak kelamaan?",
        [
            "Sebagian vitaminnya hilang, tapi tetep jauh lebih baik daripada nggak makan sayur",
            "Jadi nggak ada gunanya",
            "Malah lebih bergizi",
        ],
        0,
        "Jangan sampai takut kehilangan vitamin bikin kamu nggak makan sayur sama sekali.",
    ),
    (
        "dq-047",
        "Anjuran sayur dan buah sehari kira-kira?",
        ["1 porsi", "Sekitar 5 porsi atau 400 gram", "20 porsi"],
        1,
        "Sekitar 400 gram. Kedengeran banyak sampai kamu inget semangkok sayur itu udah 100 gram.",
    ),
    (
        "dq-048",
        "100 kalori sayur dibanding 100 kalori gorengan, di piring kelihatan?",
        ["Sayurnya jauh lebih banyak", "Sama banyak", "Gorengannya lebih banyak"],
        0,
        "100 kalori sayur itu semangkok besar, 100 kalori gorengan itu sepotong kecil. Perut ngitung isinya.",
    ),
    (
        "dq-049",
        "Nasi yang udah didinginkan (nasi kemarin) kalorinya?",
        ["Hilang separuh", "Bedanya kecil banget", "Dua kali lebih tinggi"],
        1,
        "Ada sedikit perubahan pati, tapi kecil. Jangan berharap nasi dingin jadi jalan pintas.",
    ),
    (
        "dq-050",
        "Makan siang banyak tapi jam 3 udah laper. Paling mungkin karena?",
        ["Porsinya kurang", "Minim protein dan serat", "Kurang tidur"],
        1,
        "Nasi dan gorengan doang bikin kalori masuk banyak tapi kenyangnya cepat hilang.",
    ),
    (
        "dq-051",
        "Buah manis kayak mangga dan pisang buat yang mau turun berat?",
        ["Harus dihindari", "Boleh, porsinya aja yang diatur", "Bikin diabetes"],
        1,
        "Gula buah datang bareng serat dan air. Yang jadi masalah biasanya minuman manis, bukan buah.",
    ),
    (
        "dq-052",
        "Cara gampang ngatur piring tanpa nimbang apa-apa?",
        [
            "Separuh sayur, seperempat lauk protein, seperempat karbo",
            "Semuanya nasi",
            "Cuma lauk, tanpa nasi",
        ],
        0,
        "Bisa dipakai di warteg, di rumah, di kondangan. Nggak perlu aplikasi.",
    ),
    (
        "dq-053",
        "Lalapan dan sayur mentah di warung itu?",
        ["Cara gampang nambah sayur", "Sumber lemak utama", "Nggak ada gizinya"],
        0,
        "Salah satu kebiasaan terbaik yang udah ada di makanan kita. Minta lebih banyak, gratis biasanya.",
    ),
    (
        "dq-054",
        "Sembelit paling sering karena?",
        ["Kurang serat dan air", "Kebanyakan sayur", "Kebanyakan protein"],
        0,
        "Tambah sayur, buah dan air dulu sebelum beli obat apa pun.",
    ),
    # --- latihan beban dan otot -------------------------------------------
    (
        "dq-055",
        "Yang paling bikin otot tumbuh?",
        ["Beban yang makin berat dari waktu ke waktu", "Keringat yang banyak", "Suplemen"],
        0,
        "Namanya progressive overload. Tanpa itu, badan nggak punya alasan berubah.",
    ),
    (
        "dq-056",
        "Latihan beban 2 kali seminggu buat pemula?",
        ["Terlalu sedikit, nggak ada gunanya", "Udah cukup buat kelihatan hasilnya", "Harus 6 kali"],
        1,
        "Dua kali seminggu yang rutin ngalahin enam kali seminggu yang cuma tahan dua pekan.",
    ),
    (
        "dq-057",
        "Kalau berhenti latihan, otot berubah jadi lemak?",
        [
            "Iya",
            "Nggak, itu dua jaringan beda: ototnya nyusut, lemaknya bisa nambah",
            "Cuma kejadian di cewek",
        ],
        1,
        "Nggak bisa berubah, sama kayak besi nggak bisa jadi kayu. Yang kejadian dua hal berbeda barengan.",
    ),
    (
        "dq-058",
        "Nyeri otot 1 sampai 2 hari setelah latihan itu?",
        ["Bukti latihannya berhasil", "Normal, tapi bukan ukuran keberhasilan", "Tanda cedera"],
        1,
        "Bisa muncul cuma karena gerakan baru. Yang jadi ukuran itu bebanmu naik, bukan pegelnya.",
    ),
    (
        "dq-059",
        "Buat cewek, latihan beban bikin badan?",
        [
            "Langsung gede kayak binaragawan",
            "Lebih padat dan kuat; gede butuh tahunan dan makan banyak",
            "Nggak berubah",
        ],
        1,
        "Badan besar itu proyek bertahun-tahun yang disengaja. Yang kamu dapat dari latihan biasa itu padat dan kuat.",
    ),
    (
        "dq-060",
        "Istirahat antar set buat latihan kekuatan kira-kira?",
        ["10 detik", "1 sampai 3 menit", "15 menit"],
        1,
        "Kalau istirahatnya kependekan, set berikutnya jadi jelek dan bebannya nggak bisa naik.",
    ),
    (
        "dq-061",
        "Latihan dengan beban yang sama terus selama berbulan-bulan?",
        ["Ototnya tetep nambah", "Perkembangannya berhenti", "Lebih aman jadi lebih bagus"],
        1,
        "Rutin itu syaratnya, bukan tujuannya. Naikin sedikit tiap satu dua minggu.",
    ),
    (
        "dq-062",
        "Selain penampilan, otot penting buat?",
        ["Nggak ada", "Gula darah, tulang, dan kekuatan sehari-hari", "Cuma buat atlet"],
        1,
        "Otot itu tempat gula darah dipakai. Nambah otot bikin badan lebih tahan diabetes tipe 2.",
    ),
    (
        "dq-063",
        "Umur 50 baru mulai latihan beban?",
        ["Udah telat", "Masih sangat berguna, malah makin penting", "Bahaya, mending jalan aja"],
        1,
        "Dari umur 30-an otot dan tulang turun sendiri kalau nggak dilatih. Yang mulai belakangan dapet untung paling besar.",
    ),
    (
        "dq-064",
        "Buat pemula, mana yang didahulukan?",
        ["Beban berat dulu", "Teknik dulu, bebannya nyusul", "Dua-duanya nggak penting"],
        1,
        "Teknik yang rapi bikin kamu bisa naik beban bertahun-tahun tanpa cedera. Kebalikannya nggak.",
    ),
    # --- kardio ------------------------------------------------------------
    (
        "dq-065",
        "Kardio rutin bikin jantung?",
        ["Kerja lebih boros", "Lebih efisien, denyut istirahat turun", "Nggak ngaruh"],
        1,
        "Jantung yang terlatih mompa lebih banyak per denyut, jadi kerjanya lebih santai waktu kamu istirahat.",
    ),
    (
        "dq-066",
        "Anjuran kardio sedang seminggu kira-kira?",
        ["20 menit", "Sekitar 150 menit", "20 jam"],
        1,
        "150 menit, misalnya jalan cepat 30 menit lima hari. Nggak harus di gym.",
    ),
    (
        "dq-067",
        "Jalan cepat 30 menit itu?",
        ["Nggak dihitung olahraga", "Dihitung, dan paling gampang dijalanin", "Cuma buat orang tua"],
        1,
        "Kardio yang beneran kamu lakuin tiap hari ngalahin program lari yang cuma jadi rencana.",
    ),
    (
        "dq-068",
        "Turun berat badan cuma dengan kardio, tanpa latihan beban?",
        ["Ototnya ikut hilang", "Ototnya nambah sendiri", "Nggak ada bedanya"],
        0,
        "Tanpa beban, badan nggak punya alasan nahan otot. Hasilnya lebih ringan tapi lembek, dan gampang balik.",
    ),
    (
        "dq-069",
        "Target langkah harian yang sering dipakai?",
        ["1.000 langkah", "7.000 sampai 10.000 langkah", "50.000 langkah"],
        1,
        "Manfaatnya udah kelihatan dari sekitar 7.000. Angka 10.000 aslinya dari iklan, tapi tetep patokan yang oke.",
    ),
    (
        "dq-070",
        "Soal 'fat burning zone' di alat kardio?",
        [
            "Satu-satunya cara bakar lemak",
            "Total kalori dan konsistensi lebih penting",
            "Nggak ada hubungannya sama apa pun",
        ],
        1,
        "Di intensitas rendah persentase lemaknya lebih tinggi, tapi totalnya lebih kecil. Yang penting totalnya.",
    ),
    (
        "dq-071",
        "Naik tangga tiap hari di kantor itu?",
        ["Nggak ada efek", "Kardio gratis yang nambah", "Bikin lutut rusak"],
        1,
        "Gerakan kecil yang diulang tiap hari nambahnya banyak, dan nggak butuh waktu khusus.",
    ),
    (
        "dq-072",
        "Latihan beban yang nggak bikin keringetan?",
        ["Berarti sia-sia", "Normal, keringat bukan ukuran", "Harus nambah beban dua kali lipat"],
        1,
        "Keringat itu cara badan mendinginkan diri, bukan meteran kalori atau bukti kerja keras.",
    ),
    (
        "dq-073",
        "Kalau mau latihan beban dan kardio di hari yang sama?",
        [
            "Kardio dulu sampai capek",
            "Beban dulu kalau prioritasnya kekuatan dan otot",
            "Nggak boleh sehari",
        ],
        1,
        "Yang lebih penting dikerjain waktu tenaga masih penuh. Kardio santai setelahnya nggak masalah.",
    ),
    (
        "dq-074",
        "Ngos-ngosan cuma karena naik tangga 2 lantai?",
        ["Normal buat semua orang", "Tanda kebugaran kardio kamu masih bisa dinaikin", "Tanda ototnya kurang"],
        1,
        "Kabar baiknya, ini yang paling cepat berubah. Beberapa minggu jalan cepat rutin udah kerasa.",
    ),
    # --- tidur, stres, pemulihan ------------------------------------------
    (
        "dq-075",
        "Otot dibangun paling banyak waktu?",
        ["Waktu latihan", "Waktu istirahat dan tidur", "Waktu makan"],
        1,
        "Latihan itu sinyalnya, tidur itu waktu kerjanya. Makanya kurang tidur bikin program mandek.",
    ),
    (
        "dq-076",
        "Tidur 5 jam terus-terusan biasanya bikin?",
        ["Nafsu makan naik dan tenaga turun", "Lemak lebih cepat hilang", "Nggak ada efeknya"],
        0,
        "Kurang tidur ngacak hormon lapar dan bikin angkatanmu turun. Dua-duanya lawan dari yang kamu mau.",
    ),
    (
        "dq-077",
        "Anjuran tidur orang dewasa?",
        ["4 sampai 5 jam", "7 sampai 9 jam", "12 jam"],
        1,
        "Buat banyak orang, nambah satu jam tidur lebih ngefek daripada nambah satu suplemen.",
    ),
    (
        "dq-078",
        "Stres tinggi bisa?",
        ["Bikin makan lebih banyak dan tidur lebih jelek", "Bikin otot nambah", "Nggak ada hubungannya"],
        0,
        "Stres bukan alasan, tapi memang ngaruh. Kalau lagi berat, target yang realistis lebih baik daripada nyerah.",
    ),
    (
        "dq-079",
        "Hari istirahat itu?",
        ["Tanda males", "Bagian dari programnya", "Cuma buat atlet"],
        1,
        "Badan berkembang di antara latihan, bukan waktu latihan. Istirahat itu bagian kerjanya.",
    ),
    (
        "dq-080",
        "Pemula yang latihan berat tiap hari tanpa istirahat?",
        ["Hasilnya paling cepat", "Gampang kecapekan dan cedera", "Wajib biar kebiasaan"],
        1,
        "Yang paling sering bikin orang berhenti bukan malas, tapi cedera atau capek berlebihan di bulan pertama.",
    ),
    (
        "dq-081",
        "Kafein sebelum latihan?",
        ["Bikin dehidrasi parah", "Bisa ngebantu fokus dan tenaga", "Bikin otot mengecil"],
        1,
        "Salah satu yang efeknya beneran ada. Cukup segelas kopi, dan jangan yang gulanya 6 sendok.",
    ),
    (
        "dq-082",
        "Kamu cuma tidur 4 jam dan hari ini jadwal latihan berat. Paling masuk akal?",
        [
            "Tetep latihan berat, jangan lembek",
            "Latihan ringan aja atau tidur dulu, beratnya besok",
            "Minum kopi 3 gelas biar kuat",
        ],
        1,
        "Latihan berat dengan tidur 4 jam itu risiko cedera naik dan hasilnya jelek. Program setahun nggak rusak karena satu hari.",
    ),
    # --- suplemen dan mitos ------------------------------------------------
    (
        "dq-083",
        "Suplemen yang paling banyak buktinya buat kekuatan dan otot?",
        ["Kreatin", "Fat burner", "BCAA"],
        0,
        "Kreatin: murah, paling banyak diteliti, dan aman buat orang sehat. Tetep nomor dua setelah latihan dan makan.",
    ),
    (
        "dq-084",
        "Produk 'fat burner' biasanya?",
        ["Efeknya kecil banget dibanding harganya", "Bikin lemak hilang tanpa atur makan", "Wajib buat diet"],
        0,
        "Yang ngebakar lemak itu makanmu. Fat burner paling banter ngasih efek tipis dan bikin jantung deg-degan.",
    ),
    (
        "dq-085",
        "Teh detox bikin timbangan turun 2 kg dalam 3 hari. Itu?",
        ["Lemak", "Air dan isi perut", "Otot"],
        1,
        "2 kg lemak dalam 3 hari butuh kekurangan 15.000 kalori, nggak mungkin. Yang keluar air.",
    ),
    (
        "dq-086",
        "Keringetan basah kuyup setelah olahraga artinya?",
        ["Lemak kebakar banyak", "Badan lagi mendinginkan diri", "Berat turun permanen"],
        1,
        "Beratnya balik begitu kamu minum. Latihan beban yang nggak bikin basah bisa jauh lebih ngebentuk badan.",
    ),
    (
        "dq-087",
        "Sit-up bisa ngilangin lemak perut di tempat?",
        ["Bisa kalau 500 kali sehari", "Nggak ada latihan yang bisa milih lokasi lemak", "Bisa kalau pakai sabuk pemanas"],
        1,
        "Sit-up nguatin otot perut. Yang bikin kelihatan itu lapisan lemaknya berkurang, dan itu dari makan.",
    ),
    (
        "dq-088",
        "Makan nasi jam 9 malam?",
        ["Otomatis jadi lemak", "Yang nentuin total kalori seharian", "Bikin naik 1 kg besok"],
        1,
        "Badan nggak punya jam yang bilang 'lewat jam 8 disimpen jadi lemak'.",
    ),
    (
        "dq-089",
        "Madu dibanding gula pasir?",
        ["Madu bebas kalori", "Dua-duanya gula, kalorinya mirip", "Madu 10 kali lebih tinggi"],
        1,
        "Madu ada sedikit mikronutrien, tapi tetep gula. Dituang banyak tetep banyak kalorinya.",
    ),
    (
        "dq-090",
        "Multivitamin buat orang yang makannya udah beragam?",
        ["Wajib tiap hari", "Biasanya nggak perlu", "Bikin gendut"],
        1,
        "Kalau makanmu udah macam-macam, uangnya lebih berguna buat telur, ikan dan sayur.",
    ),
    # --- makanan sini, hitungan warung, puasa ------------------------------
    (
        "dq-091",
        "Batagor 1 porsi lengkap sama bumbu kacang kira-kira?",
        ["150 kalori", "400 sampai 500 kalori", "1.500 kalori"],
        1,
        "Digoreng plus bumbu kacang. Enak, cuma jangan dianggap camilan ringan.",
    ),
    (
        "dq-092",
        "Semangkok mie kocok kira-kira?",
        ["200 kalori", "400 sampai 500 kalori", "1.200 kalori"],
        1,
        "Sekitar 400 sampai 500. Kalau ditambah nasi, itu dua sumber karbo dalam satu duduk.",
    ),
    (
        "dq-093",
        "Seblak kalorinya kebanyakan datang dari?",
        ["Pedesnya", "Kerupuk dan minyaknya", "Sayurnya"],
        1,
        "Kerupuk basah tetep kerupuk yang digoreng sebelumnya. Pedes nggak nambah dan nggak ngurangin kalori.",
    ),
    (
        "dq-094",
        "Di gado-gado atau lotek, proteinnya datang dari?",
        ["Bumbu kacang, tahu, tempe dan telurnya", "Nasinya", "Kerupuknya"],
        0,
        "Salah satu makanan kita yang paling seimbang. Yang perlu diatur cuma jumlah bumbu kacang dan kerupuknya.",
    ),
    (
        "dq-095",
        "Makan nasi padang tapi mau lebih terkontrol. Paling masuk akal?",
        [
            "Hindari total",
            "Sayur lebih banyak, lauk yang dibakar atau direbus, kuah santan dikurangi",
            "Cuma makan rendang tanpa nasi",
        ],
        1,
        "Nggak ada makanan yang harus dihapus. Yang diatur cara masak lauknya dan seberapa banyak kuahnya.",
    ),
    (
        "dq-096",
        "Bubur ayam plus kerupuk plus cakwe. Mana yang paling nambah kalori tanpa nambah kenyang?",
        ["Ayamnya", "Kerupuk dan cakwenya", "Buburnya"],
        1,
        "Dua-duanya digoreng. Buburnya sendiri sebenernya porsi karbo yang lumayan terkontrol.",
    ),
    (
        "dq-097",
        "Es campur atau es doger kalorinya?",
        ["Rendah karena isinya buah", "Lumayan tinggi dari kental manis dan sirupnya", "Hampir nol"],
        1,
        "Buahnya bagus, yang nambah kalori itu kental manis, sirup dan susu manisnya.",
    ),
    (
        "dq-098",
        "Waktu puasa, kapan paling masuk akal latihan beban?",
        ["Tengah hari", "Dekat waktu buka atau setelah buka", "Nggak latihan sama sekali sebulan"],
        1,
        "Dekat buka berarti kamu bisa langsung minum dan makan setelahnya. Berhenti total sebulan bikin mulai lagi jadi berat.",
    ),
    (
        "dq-099",
        "Sahur yang bikin tahan lapar sampai sore?",
        ["Cuma nasi dan kerupuk", "Ada protein dan serat: telur, tempe, sayur, buah", "Kopi doang"],
        1,
        "Protein dan serat yang bikin kenyangnya panjang. Sahur nasi doang bikin jam 10 udah lemes.",
    ),
    (
        "dq-100",
        "Kopi susu gula aren tiap hari plus latihan rutin, hasilnya sering?",
        [
            "Berat nggak turun karena minumannya",
            "Otomatis turun karena udah latihan",
            "Nggak ada hubungannya",
        ],
        0,
        "Satu gelas kira-kira 250 kalori, dan satu jam latihan 200 sampai 400. Satu minuman bisa ngehabisin hasil satu sesi.",
    ),
]


def _build(rows):
    """Turn the compact rows into what the model stores.

    The correct answer is moved to a slot derived from the question's code (see
    nutrition/shuffle.py). Written by hand, 77 of these 100 had the answer at B
    and none at C, so "always pick the middle one" scored 77% without reading.
    Write the answer wherever it reads best here; placement is handled for you.
    """
    letters = "abcdefgh"
    built = []
    for position, (code, question, choices, answer_index, explanation) in enumerate(
        rows, start=1
    ):
        authored = [
            {"key": letters[index], "text": text} for index, text in enumerate(choices)
        ]
        placed, answer = place_answer(code, authored, letters[answer_index])
        built.append(
            {
                "code": code,
                "position": position,
                "question": question,
                "choices": placed,
                "answer": answer,
                "explanation": explanation,
            }
        )
    return built


QUESTIONS = _build(RAW)
