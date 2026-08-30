"""The daily quiz questions, seeded into the database by a migration.

Format is deliberately compact so a human can review a hundred of them without
losing the will to live:

    ("code", "topic", "question", ["choice a", "choice b", "choice c", "choice d"],
     answer_index, "explanation")

`_build` turns each row into the shape the model stores: choices keyed a/b/c/d
and the answer as a letter.

**The order of this list is not the order members see.** Grouping by topic is for
whoever reviews the file; walking that order gave members twelve straight days of
calories, then twelve of protein. `nutrition/interleave.py` computes a rotation
that never puts two of the same topic together, and a migration writes it into
`position`, which is what actually decides the day. So `position` in a built row
is the file order and only decides where an *appended* question lands: at the
end, until a migration spreads it in.

Rules for editing:

- **A `code` is permanent.** It is the key the seeding migration matches on and
  what every recorded answer points at, so renaming one orphans its history.
  Reorder freely, rename never.
- **Adding questions**: append to the end, give it a `topic` (a new one is fine),
  and add a migration that calls the same sync helper. It lands after everything
  else in the rotation until a migration interleaves the unshown tail again, so a
  batch worth spreading needs that second step (see `0006_spread_daily_topics`).
- **Everything from `dq-007` on has to make somebody think.** Four choices rather
  than three (a blind guess drops from 33% to 25%), and an answer that needs
  working out (do the arithmetic), judging (all four are true, which matters
  most?), or unlearning something (the intuitive answer is the wrong one). Hard is
  not the same as obscure: no trivia, no trick wording, and never two defensible
  answers. `dq-001` to `dq-006` are the original five-second questions, left as
  they are because members have already answered them.
- **Rewriting a question that exists** does nothing to a seeded database on its
  own, because `sync_questions` never overwrites. It needs a migration calling
  `rewrite_questions`, and only for codes nobody has answered yet: a recorded
  answer is just a letter, so changing the choices under it would point it at
  different text. See `0005_harder_daily_questions`.
- **Editing wording after launch**: change it in `/admin`. Editing here alone does
  nothing to a database that has already been seeded.
- Every number is an estimate and says so. Portions vary by warung.
"""

from .shuffle import place_answer

RAW = [
    # --- kalori dan berat badan -------------------------------------------
    #
    # dq-001 to dq-006 are the original three-choice questions, answerable in
    # about five seconds. Kept as they are: members have answered them, and the
    # letter recorded against each one has to keep pointing at the same text.
    (
        "dq-001",
        "kalori",
        "Mana yang paling padat kalori per gram?",
        ["Minyak", "Gula", "Protein"],
        0,
        "Minyak 9 kalori per gram, gula dan protein cuma 4. Makanya minyak paling gampang bikin kalori naik tanpa kelihatan.",
    ),
    (
        "dq-002",
        "kalori",
        "Buat nurunin 1 kg lemak badan, kira-kira butuh kekurangan kalori sebanyak?",
        ["1.000 kalori", "7.700 kalori", "50.000 kalori"],
        1,
        "Kira-kira 7.700. Itu kenapa turun setengah kilo seminggu udah bagus, dan kenapa 'turun 5 kg dalam 3 hari' itu air, bukan lemak.",
    ),
    (
        "dq-003",
        "kalori",
        "Timbangan naik 1 kg dari kemarin. Paling mungkin itu?",
        ["Lemak baru", "Air dan isi perut", "Otot baru"],
        1,
        "Lemak nggak bisa nambah 1 kg dalam sehari, itu butuh kelebihan 7.700 kalori. Yang naik air, garam, dan isi perut.",
    ),
    (
        "dq-004",
        "kalori",
        "Turun berat badan yang realistis dan aman itu kira-kira?",
        ["0,3 sampai 0,7 kg per minggu", "2 sampai 3 kg per minggu", "5 kg per minggu"],
        0,
        "Lebih cepat dari itu biasanya air dan otot yang ikut hilang, dan hampir selalu balik lagi.",
    ),
    (
        "dq-005",
        "kalori",
        "Nasi putih 1 centong (kira-kira 100 gram) itu berapa kalori?",
        ["Sekitar 50", "Sekitar 130", "Sekitar 400"],
        1,
        "Sekitar 130. Nasi sering disalahin padahal porsinya yang perlu diatur, bukan nasinya yang jahat.",
    ),
    (
        "dq-006",
        "kalori",
        "5 keping kerupuk kira-kira setara?",
        ["Sekitar 30 kalori", "Sekitar 150 kalori", "Sekitar 500 kalori"],
        1,
        "Sekitar 150, karena kerupuk digoreng dan nyerep minyak. Kenyangnya nol.",
    ),
    #
    # From here on: four choices, and an answer that needs arithmetic, judgment
    # or unlearning. The numbers are the same ones dq-001 to dq-006 and the
    # chapters teach, so the harder questions put them to work.
    (
        "dq-007",
        "kalori",
        "Dua orang makan ayam penyet yang sama persis, tapi tebakan kalorinya beda 300. Paling mungkin karena?",
        [
            "Yang satu ngitung minyak dan gula di bumbunya, yang satu nggak",
            "Yang satu makannya lebih pelan, jadi kalorinya kepakai duluan",
            "Yang satu badannya lebih besar, jadi kalori makanannya lebih tinggi",
            "Kalori makanan warung memang nggak bisa dikira-kira sama sekali",
        ],
        0,
        "Bahan yang kelihatan gampang ditebak. Yang bikin meleset ratusan itu minyak goreng, santan dan gula di bumbu, karena nggak ada yang nyebutin jumlahnya. Badan yang makan nggak ngubah kalori makanannya.",
    ),
    (
        "dq-008",
        "kalori",
        "Empat orang sama-sama turun 4 kg dalam sebulan. Setahun lagi, siapa yang paling mungkin masih di berat barunya?",
        [
            "Yang cuma ngurangin gorengan dan minuman manis, sisanya makan normal",
            "Yang berhenti total makan nasi",
            "Yang makan cuma sekali sehari, dan ngerasa itu yang paling gampang",
            "Yang ikut program 30 hari tanpa karbo dan tanpa gula",
        ],
        0,
        "Yang bertahan setahun itu aturan yang bisa kamu jalanin tanpa mikir tiap hari. Tiga lainnya menang di bulan pertama dan kalah di bulan ketiga, karena nggak ada yang tahan hidup begitu bertahun-tahun.",
    ),
    (
        "dq-009",
        "kalori",
        "Berat kamu nggak gerak 3 minggu, padahal kamu ngerasa udah ngurangin makan. Paling masuk akal?",
        [
            "Kalori yang masuk dan yang kepakai udah imbang, tanpa kamu sadari",
            "Metabolisme kamu rusak",
            "Badan nyimpen lemak karena ngerasa kalorinya kurang, jadi nahan",
            "Timbangannya yang nggak akurat",
        ],
        0,
        "Berat yang stabil itu tanda masukan dan pemakaian ketemu di angka yang sama. Biasanya bukan karena badan rusak, tapi karena porsi pelan-pelan balik atau ada yang lupa dihitung, dan minuman paling sering.",
    ),
    (
        "dq-010",
        "kalori",
        "Kamu selalu nambah nasi begitu piring pertama habis. Yang paling ngebantu?",
        [
            "Tunggu 15 menit dulu sebelum mutusin nambah",
            "Nambah nasi, tapi lauknya nggak usah",
            "Ganti nasi putih ke nasi merah, porsinya tetep",
            "Makan lebih cepat biar cepat selesai",
        ],
        0,
        "Rasa kenyang butuh sekitar 20 menit buat nyampe otak, jadi kalau kamu mutusin nambah di menit ke-8, kamu mutusin sebelum badan sempat ngasih kabar. Ngurangin lauk malah kebalikannya: protein itu yang bikin kenyangnya tahan.",
    ),
    (
        "dq-011",
        "kalori",
        "Treadmill bilang kamu bakar 400 kalori, terus kamu 'bayar' pakai kopi susu gula aren 250 kalori. Masalahnya?",
        [
            "Angka alatnya sering kelebihan, jadi kembaliannya nggak sebanyak itu",
            "Kopi susu nggak usah dihitung, yang penting latihannya jalan",
            "Kalori latihan cuma bisa dibayar pakai makanan, minuman nggak ngitung",
            "Nggak ada masalah, itungannya pas",
        ],
        0,
        "Alatnya nggak tahu berat, umur dan efisiensi gerak kamu, dan angkanya biasanya lebih tinggi dari yang sebenarnya. Kalau tiap latihan dibayar minuman, hasil satu sesi bisa habis tanpa kelihatan.",
    ),
    (
        "dq-012",
        "kalori",
        "Dua piring sama-sama 600 kalori: satu nasi banyak plus gorengan, satu nasi sedikit plus ayam bakar dan sayur banyak. Bedanya?",
        [
            "Yang kedua bikin kenyang jauh lebih lama, padahal kalorinya sama",
            "Yang kedua kalorinya jadi lebih rendah",
            "Sama aja, kalori yang sama efeknya sama",
            "Yang pertama lebih bikin kenyang karena porsinya lebih berat",
        ],
        0,
        "Kalori yang sama nggak berarti kenyang yang sama. Protein dan serat yang bikin tahan sampai sore, jadi piring kedua bikin kamu nggak nyari cemilan jam 3, tanpa nambah kalori sepeser pun.",
    ),
    # --- protein ----------------------------------------------------------
    (
        "dq-013",
        "protein",
        "Kamu naikin sarapan dari 1 telur jadi 3 telur, tiap hari. Dalam seminggu, protein tambahannya kira-kira?",
        ["Sekitar 90 gram", "Sekitar 15 gram", "Sekitar 40 gram", "Sekitar 250 gram"],
        0,
        "Satu telur sedang sekitar 6 sampai 7 gram, jadi nambah 2 telur itu sekitar 13 gram sehari dan sekitar 90 gram seminggu, hampir setara kebutuhan sehari penuh orang 60 kg. Perubahan kecil yang diulang itu yang nambahnya banyak.",
    ),
    (
        "dq-014",
        "protein",
        "Tempe sepotong ukuran sedang kira-kira 50 gram. Buat dapet 40 gram protein dari tempe doang, butuh berapa potong?",
        ["Sekitar 4 potong", "Sekitar 2 potong", "Sekitar 8 potong", "Sekitar 12 potong"],
        0,
        "100 gram tempe sekitar 19 gram protein, jadi sepotong 50 gram sekitar 9 sampai 10 gram. Empat potong udah sekitar 40 gram, dengan harga yang nggak ada lawannya di pasar.",
    ),
    (
        "dq-015",
        "protein",
        "Target protein 96 gram sehari (orang 60 kg). Sepotong ayam dada 150 gram nutup berapa persen dari target itu?",
        ["Sekitar 35%", "Sekitar 10%", "Sekitar 60%", "Hampir semuanya"],
        0,
        "150 gram ayam dada sekitar 34 gram protein, jadi kira-kira sepertiga target. Artinya sekali makan lauk besar aja belum cukup: protein perlu ada di tiap kali makan, bukan numpuk di satu piring.",
    ),
    (
        "dq-016",
        "protein",
        "Berat 75 kg dan latihan rutin. Target protein hariannya kira-kira?",
        ["Sekitar 120 gram", "Sekitar 40 gram", "Sekitar 75 gram", "Sekitar 250 gram"],
        0,
        "Patokannya sekitar 1,6 gram per kilo, jadi 75 kali 1,6 sekitar 120 gram. Angka 75 gram itu 1 gram per kilo, patokan buat yang nggak latihan, bukan buat yang mau nambah otot.",
    ),
    (
        "dq-017",
        "protein",
        "Empat cemilan ini sama-sama sekitar 200 kalori. Mana yang paling bikin kamu nggak nyari makan lagi sejam kemudian?",
        [
            "2 telur rebus plus sebuah pisang",
            "Satu roti manis isian cokelat",
            "Sekantong kecil kerupuk udang",
            "Dua gelas es teh manis dingin",
        ],
        0,
        "Kalorinya mirip, rasa kenyangnya nggak. Protein dan serat yang bikin tahan lama, sementara gula dan gorengan lewat cepat dan bikin kamu nyari lagi. Yang dihitung perut itu isinya, bukan cuma kalorinya.",
    ),
    (
        "dq-018",
        "protein",
        "Kamu makan 3 kali sehari pakai lauk, dan protein hariannya udah nyampe target. Whey protein buat kamu?",
        [
            "Nggak nambah apa-apa selain kepraktisan",
            "Tetep wajib kalau mau nambah otot",
            "Bikin ototnya nambah lebih cepat daripada dari makanan",
            "Bahaya kalau protein dari makanan udah cukup",
        ],
        0,
        "Whey itu cuma protein yang dibikin gampang diminum, bukan bahan yang beda. Kalau totalmu udah cukup, dia nggak nambah hasil. Yang beneran ngebantu itu kalau kamu susah makan atau lagi buru-buru.",
    ),
    (
        "dq-019",
        "protein",
        "Sehari kamu dapet 100 gram protein dari tempe, tahu, telur dan ikan. Dibanding 100 gram dari ayam dan whey doang?",
        [
            "Buat bikin otot, hasilnya kurang lebih sama",
            "Yang nabati nggak dihitung, jadi kamu sebenernya kurang",
            "Yang nabati malah lebih bagus buat otot",
            "Cuma protein hewani yang kepake buat otot",
        ],
        0,
        "Yang nentuin itu total protein sehari dan variasi sumbernya, bukan nabati atau hewani. Tempe dan tahu dihitung penuh, dan campuran macam-macam sumber malah nutup kekurangan masing-masing.",
    ),
    (
        "dq-020",
        "protein",
        "Kamu latihan jam 7 malam dan baru bisa makan jam 9. Ototnya?",
        [
            "Nggak masalah, yang nentuin total protein hari itu",
            "Kelewat, jendela 30 menit setelah latihan udah ketutup",
            "Cuma kebentuk separuh",
            "Malah lebih bagus kalau makannya ditunda",
        ],
        0,
        "Jendela 30 menit itu mitos lama. Badan masih ngerjain protein berjam-jam setelah latihan, jadi yang penting total hari itu cukup, bukan menitnya pas.",
    ),
    (
        "dq-021",
        "protein",
        "Kamu ganti 1 gelas es teh manis sehari jadi 1 gelas susu cair. Sebulan, protein tambahannya kira-kira?",
        [
            "Sekitar 240 gram",
            "Sekitar 30 gram",
            "Sekitar 800 gram",
            "Nggak nambah, dua-duanya cuma minuman",
        ],
        0,
        "Susu cair 250 ml sekitar 8 gram protein, jadi sebulan sekitar 240 gram, dan kamu sekalian buang sekitar 5 sendok teh gula per gelas. Satu tuker-tukeran, dua untung.",
    ),
    (
        "dq-022",
        "protein",
        "Uang lauk cuma cukup buat satu. Mana yang ngasih protein plus sesuatu yang susah didapet dari lauk lain?",
        ["Ikan kembung", "Ayam dada", "Telur", "Tempe"],
        0,
        "Empat-empatnya sumber protein bagus, sekitar 19 sampai 23 gram per 100 gram. Bedanya ikan kembung bawa omega-3 yang hampir nggak ada di tiga lainnya, dan harganya masih murah di pasar.",
    ),
    (
        "dq-023",
        "protein",
        "Sarapan kamu nasi kuning plus kerupuk, siangnya nasi plus gorengan. Satu perubahan yang paling nambah protein?",
        [
            "Tambah 1 telur di sarapan dan sepotong tempe di siang",
            "Ganti nasi putih ke nasi merah",
            "Kerupuknya diganti kerupuk yang lebih kecil dan tipis",
            "Nasinya dikurangi separuh",
        ],
        0,
        "Nasi merah dan porsi nasi nggak nambah protein sama sekali, jadi masalahnya nggak kepegang. Satu telur plus sepotong tempe itu sekitar 16 gram, murah, dan ada di warung mana aja.",
    ),
    (
        "dq-024",
        "protein",
        "Kamu sehat, ginjal normal, makan sekitar 1,8 gram protein per kilo. Yang bener?",
        [
            "Nggak ada bukti itu bikin masalah buat ginjal yang sehat",
            "Ginjalnya pasti rusak dalam beberapa tahun",
            "Aman cuma kalau proteinnya dari tumbuhan",
            "Aman cuma kalau kamu minum air 5 liter sehari buat ngebilas",
        ],
        0,
        "Buat orang sehat nggak ada buktinya. Anjuran protein rendah itu buat orang yang udah punya penyakit ginjal, dan itu beda cerita: kalau kamu punya, tanya dokter dulu.",
    ),
    # --- gula dan minuman -------------------------------------------------
    (
        "dq-025",
        "minuman",
        "Es teh manis 2 gelas sehari, tiap hari, dan sisanya nggak berubah. Setahun kira-kira setara berapa kilo lemak?",
        [
            "Sekitar 10 kg",
            "Sekitar 1 kg",
            "Sekitar 3 kg",
            "Nggak ngaruh, namanya cuma minuman",
        ],
        0,
        "Satu gelas sekitar 110 kalori, dua gelas 220, setahun sekitar 80.000 kalori. Dibagi 7.700 per kilo lemak, itu sekitar 10 kg. Angka kecil yang diulang tiap hari itu yang paling sering nggak kelihatan.",
    ),
    (
        "dq-026",
        "minuman",
        "Batas gula tambahan sehari sekitar 50 gram. Sekaleng soda (35 gram) plus segelas es teh manis (sekitar 25 gram), kamu di mana?",
        [
            "Udah lewat batasnya",
            "Masih di separuh batas",
            "Pas di batasnya",
            "Masih jauh, batasnya sekitar 150 gram",
        ],
        0,
        "35 plus 25 itu 60 gram, udah lewat sebelum kamu makan apa pun. Itu kenapa minuman biasanya jadi target pertama: dia ngabisin jatah gula tanpa ngasih kenyang sedikit pun.",
    ),
    (
        "dq-027",
        "minuman",
        "Anak dikasih susu kental manis tiap pagi biar 'kuat'. Masalah terbesarnya?",
        [
            "Isinya kira-kira separuh gula, proteinnya jauh di bawah susu cair",
            "Nggak ada masalah, namanya juga susu, dari dulu begitu",
            "Cuma bikin gigi rusak, gizinya sendiri nggak masalah",
            "Kalorinya kurang buat anak yang lagi tumbuh, jadi perlu ditambah",
        ],
        0,
        "Kental manis itu lebih dekat ke sirup daripada susu: sekitar separuhnya gula, proteinnya sedikit. Buat anak yang butuh protein buat tumbuh, itu tuker yang mahal. Susu cair biasa jauh lebih masuk akal.",
    ),
    (
        "dq-028",
        "minuman",
        "Kamu minum soda bergula 2 kaleng sehari dan mau turun berat badan. Paling masuk akal?",
        [
            "Pindah ke air putih, dan soda zero kalau butuh transisi",
            "Tetep soda bergula, yang penting latihannya ditambah",
            "Soda zero seharian, sebanyak apa pun",
            "Ganti jus buah kemasan",
        ],
        0,
        "Dua kaleng itu sekitar 70 gram gula dan 300 kalori yang nggak bikin kenyang. Air putih tujuannya, soda zero jembatannya kalau berhenti langsung kerasa berat. Jus kemasan gulanya nggak jauh beda.",
    ),
    (
        "dq-029",
        "minuman",
        "Kopi susu gula aren sekitar 250 kalori, kopi hitam hampir nol. Kalau yang pertama diminum tiap hari kerja, sebulan?",
        [
            "Sekitar 5.000 kalori, kira-kira 0,7 kg lemak",
            "Sekitar 1.000 kalori, kira-kira 0,1 kg lemak",
            "Sekitar 20.000 kalori, kira-kira 2,6 kg lemak",
            "Nggak ada bedanya sama kopi hitam",
        ],
        0,
        "20 hari kerja kali 250 itu sekitar 5.000 kalori, sekitar 0,7 kg lemak sebulan kalau yang lain nggak berubah. Bukan berarti haram, cuma perlu dianggap makanan, bukan minuman.",
    ),
    (
        "dq-030",
        "minuman",
        "Boba 500 ml sekitar 400 kalori, dan sepiring nasi plus ayam bakar dan sayur juga sekitar 400. Bedanya yang paling penting?",
        [
            "Yang kedua bikin kenyang berjam-jam dan ngasih protein",
            "Yang pertama kalorinya lebih cepat kebakar",
            "Nggak ada bedanya, kalorinya sama",
            "Yang kedua lebih gampang bikin gendut karena ada nasinya",
        ],
        0,
        "Kalorinya sama, hasilnya beda jauh. Boba lewat tanpa ngasih protein dan tanpa bikin kenyang, jadi kamu tetep makan lagi setelahnya. Piring makanan beneran ngitung sebagai makan.",
    ),
    (
        "dq-031",
        "minuman",
        "Segelas jus jeruk butuh sekitar 3 jeruk. Kalau kamu makan 3 jeruk utuh?",
        [
            "Lebih kenyang, dan biasanya berhenti sebelum yang ketiga",
            "Sama aja, gula yang masuk sama banyaknya",
            "Kalorinya jadi jauh lebih tinggi daripada jusnya",
            "Vitaminnya kurang kepake dibanding kalau bentuknya jus",
        ],
        0,
        "Gulanya mirip, tapi serat dan volumenya bikin kamu penuh. Gampang minum gula 3 jeruk dalam 30 detik, susah makan 3 jeruk utuh sekali duduk. Itu bedanya yang beneran kepake.",
    ),
    (
        "dq-032",
        "minuman",
        "Jam 4 sore kamu laper, padahal makan siang jam 1 lauknya lengkap. Yang masuk akal dicoba dulu?",
        [
            "Minum air, tunggu 15 menit, baru putusin",
            "Langsung beli gorengan biar cepat hilang",
            "Tahan sampai makan malam apa pun yang terjadi",
            "Minum kopi manis biar nggak kepikiran",
        ],
        0,
        "Haus sering kebaca sebagai laper, sinyalnya mirip. Minum dulu itu tes yang murah dan cepat. Kalau 15 menit kemudian masih laper, makan cemilan yang ada proteinnya, bukan gorengan.",
    ),
    (
        "dq-033",
        "minuman",
        "Kamu latihan sejam sampai basah kuyup, di Bandung yang lembap. Kebutuhan cairan hari itu?",
        [
            "Naik sekitar setengah sampai satu liter dari biasanya",
            "Sama aja dengan hari biasa, badannya udah biasa",
            "Turun, karena badan udah nyimpen air waktu latihan",
            "Naik jadi sekitar 8 liter biar keringatnya kegantiin",
        ],
        0,
        "Patokan hariannya sekitar 2 sampai 3 liter, dan latihan yang bikin basah nambah sekitar setengah sampai satu liter. Warna pipis yang gelap itu tanda paling gampang dibaca.",
    ),
    (
        "dq-034",
        "minuman",
        "Kamu baru ngerasa haus di menit ke-40 latihan. Artinya?",
        [
            "Kamu udah mulai kurang cairan sebelum itu, hausnya telat",
            "Cairanmu masih pas, haus itu sinyalnya datang tepat waktu",
            "Kamu kelebihan air, jadi sinyalnya jadi kebalik",
            "Kamu latihan terlalu keras buat ukuran badanmu",
        ],
        0,
        "Haus itu alarm yang nyala setelah kurangnya mulai, bukan pas mulai. Makanya waktu latihan minumnya dijadwal, sedikit-sedikit tiap 15 menit, bukan nunggu badan minta.",
    ),
    # --- gorengan, minyak, cara masak -------------------------------------
    (
        "dq-035",
        "gorengan",
        "Tumis sayur pakai 3 sendok makan minyak. Kalori dari minyaknya doang kira-kira?",
        [
            "Sekitar 360",
            "Sekitar 120",
            "Sekitar 40",
            "Nol, minyaknya ketinggalan di wajan",
        ],
        0,
        "Satu sendok makan sekitar 120 kalori, jadi tiga sendok sekitar 360, lebih tinggi dari sepiring nasinya. Minyak yang nyerep ke sayur ikut masuk, jadi tumis sedikit minyak beda jauh sama tumis banjir.",
    ),
    (
        "dq-036",
        "gorengan",
        "Dua wajan: minyaknya yang satu kurang panas, yang satu udah panas betul. Tempe goreng di mana yang nyerep minyak lebih banyak?",
        [
            "Di yang minyaknya kurang panas",
            "Di yang minyaknya udah panas betul",
            "Sama aja, yang nentuin lama gorengnya",
            "Tergantung merek minyaknya",
        ],
        0,
        "Minyak panas langsung bikin lapisan luar yang nahan, jadi masuknya lebih sedikit. Minyak kurang panas bikin makanan kelamaan berenang di dalam dan nyerep terus. Ini kebalikan dari yang biasa dikira.",
    ),
    (
        "dq-037",
        "gorengan",
        "Kamu ganti ayam goreng tepung jadi ayam bakar, sekali sehari, selama sebulan. Kira-kira?",
        [
            "Sekitar 4.500 kalori lebih rendah, kira-kira 0,6 kg lemak",
            "Sekitar 500 kalori lebih rendah, kira-kira 0,06 kg lemak",
            "Sekitar 20.000 kalori lebih rendah, kira-kira 2,6 kg lemak",
            "Nggak ada bedanya, proteinnya sama",
        ],
        0,
        "Bedanya sekitar 150 kalori sepotong, jadi sebulan sekitar 4.500, kira-kira setengah kilo lemak. Proteinnya sama persis, jadi kamu nggak kehilangan apa-apa selain cara masaknya.",
    ),
    (
        "dq-038",
        "gorengan",
        "Tempe 100 gram bisa jadi sekitar 190 kalori atau sekitar 340. Yang nentuin?",
        [
            "Cara masaknya, dikukus atau digoreng",
            "Merek tempenya",
            "Dimakan pagi atau malam",
            "Tempenya masih baru atau udah lama",
        ],
        0,
        "Bahan yang sama bisa beda ratusan kalori cuma dari minyak yang nyerep. Kukus, rebus, bakar, atau tumis sedikit minyak: itu tuas yang paling gede dan paling gampang dipakai tiap hari.",
    ),
    (
        "dq-039",
        "gorengan",
        "Satu centong nasi sekitar 130 kalori. 10 keping kerupuk kira-kira?",
        [
            "Sekitar 300 kalori, dua kali lipat nasinya",
            "Sekitar 60 kalori, jauh di bawah nasinya",
            "Sekitar 150 kalori, sama dengan nasinya",
            "Nol, kerupuk isinya cuma udara",
        ],
        0,
        "Lima keping sekitar 150 kalori, jadi sepuluh sekitar 300, dua kali lipat satu centong nasi. Kerupuk itu gorengan yang nggak dianggap gorengan, dan kenyangnya nol.",
    ),
    (
        "dq-040",
        "gorengan",
        "Minyak kelapa, minyak zaitun, minyak sawit. Kalori per gramnya?",
        [
            "Sama semua, sekitar 9 kalori per gram",
            "Minyak kelapa paling rendah karena lemak sehat",
            "Minyak zaitun paling rendah",
            "Bedanya sampai dua kali lipat",
        ],
        0,
        "Sehat atau nggak, semua minyak sekitar 9 kalori per gram. Yang beda profil lemaknya, bukan kalorinya, jadi 'ganti ke minyak sehat' nggak ngasih izin nambah jumlahnya.",
    ),
    (
        "dq-041",
        "gorengan",
        "Kuah gulai kamu habisin sampai bersih, kira-kira 200 ml santan kental. Kalori dari kuahnya doang?",
        [
            "Sekitar 400",
            "Sekitar 100",
            "Sekitar 50, namanya cuma kuah",
            "Sekitar 1.000",
        ],
        0,
        "Santan kental sekitar 200 kalori per 100 ml, jadi 200 ml sekitar 400, setara sepiring nasi lebih. Bukan berarti santan haram: kuahnya nggak perlu diminum sampai habis, itu aja.",
    ),
    (
        "dq-042",
        "gorengan",
        "Kamu makan 4 potong gorengan tiap hari dan nggak mau berhenti total. Mana yang paling mungkin jalan setahun?",
        [
            "Turunin jadi 1 potong, sisa kebiasaannya tetep",
            "Berhenti total mulai besok",
            "Ganti semua gorengan jadi kerupuk",
            "Tetep 4 potong, tapi latihan ditambah 30 menit",
        ],
        0,
        "Aturan yang bisa dijalanin menang. Kerupuk juga digoreng, jadi itu cuma pindah tempat, dan 3 potong gorengan itu sekitar 300 kalori, lebih besar dari yang kebakar di 30 menit tambahan.",
    ),
    (
        "dq-043",
        "gorengan",
        "Kamu potong lemak sampai hampir nol biar cepat turun. Yang paling mungkin kejadian?",
        [
            "Hormon dan penyerapan vitamin tertentu keganggu",
            "Turunnya paling cepat dan paling sehat",
            "Nggak ada efeknya, lemak nggak dibutuhin badan",
            "Ototnya nambah lebih cepat",
        ],
        0,
        "Lemak dibutuhin buat hormon dan buat nyerap vitamin A, D, E dan K. Yang perlu diatur jumlahnya, bukan dihapus, dan makanan tanpa lemak biasanya nggak ada yang tahan lebih dari beberapa minggu.",
    ),
    (
        "dq-044",
        "gorengan",
        "Salad sayur 100 kalori dikasih 3 sendok makan mayones. Totalnya?",
        [
            "Sekitar 370 kalori",
            "Sekitar 130 kalori",
            "Sekitar 190 kalori",
            "Tetep 100, mayones cuma saus",
        ],
        0,
        "Satu sendok mayones sekitar 90 kalori, hampir semuanya minyak, jadi tiga sendok nambah sekitar 270. Sausnya bisa lebih tinggi dari sayurnya, dan itu kejadian paling sering di menu yang kelihatan sehat.",
    ),
    # --- sayur, serat, rasa kenyang ---------------------------------------
    (
        "dq-045",
        "serat",
        "Dua sarapan sama-sama sekitar 350 kalori: bubur ayam, atau oat plus buah dan telur. Jam 11 siapa yang lebih tahan?",
        [
            "Yang kedua, karena serat dan proteinnya lebih tinggi",
            "Yang pertama, karena hangat dan berkuah",
            "Sama, kalorinya sama",
            "Yang pertama, karena nasi lebih ngenyangin daripada oat",
        ],
        0,
        "Serat nambah volume dan bikin pencernaan jalan lebih pelan, protein nahan lapar. Bubur ayam kalorinya sama tapi lewat cepat, jadi jam 11 kamu udah nyari cemilan.",
    ),
    (
        "dq-046",
        "serat",
        "Sayur di rumah kamu selalu dimasak sampai lembek banget. Sikap yang paling masuk akal?",
        [
            "Tetep makan, sambil pelan-pelan masaknya dipersingkat",
            "Berhenti makan sayur karena vitaminnya udah hilang",
            "Ganti sayurnya jadi multivitamin",
            "Nggak usah diubah, masak lama malah nambah gizinya",
        ],
        0,
        "Sebagian vitamin memang hilang, tapi serat, mineral dan volumenya utuh. Sayur lembek jauh lebih baik daripada nggak ada sayur, dan takut kehilangan vitamin nggak boleh jadi alasan berhenti.",
    ),
    (
        "dq-047",
        "serat",
        "Anjurannya sekitar 400 gram sayur dan buah sehari. Kalau semangkok sayur sekitar 100 gram, sehari butuh?",
        [
            "Sekitar 4 mangkok, atau 3 mangkok plus sebuah buah",
            "Semangkok",
            "Sekitar 10 mangkok",
            "Nggak perlu dihitung, sayur nggak ada patokannya",
        ],
        0,
        "Kedengeran banyak sampai dibagi: semangkok tiap kali makan plus satu buah udah nyampe. Lalapan di warung ngitung juga, dan itu biasanya gratis kalau minta lebih.",
    ),
    (
        "dq-048",
        "serat",
        "Kamu diminta ngabisin 500 kalori sayur bening dalam sekali duduk. Paling mungkin?",
        [
            "Nggak kekejar, perutnya penuh duluan",
            "Gampang, sayur nggak ngenyangin",
            "Gampang, tinggal ditemenin nasi",
            "Nggak mungkin, sayur nggak ada kalorinya",
        ],
        0,
        "500 kalori sayur bening itu bermangkok-mangkok, sementara 500 kalori gorengan itu tiga potong. Perut ngitung isinya, bukan kalorinya, dan itu yang bikin sayur ngebantu ngatur porsi.",
    ),
    (
        "dq-049",
        "serat",
        "Nasi kemarin yang udah dingin dipanasin lagi. Kalorinya dibanding nasi baru?",
        [
            "Bedanya kecil banget, jangan diandalkan",
            "Turun separuh karena patinya berubah",
            "Naik dua kali karena dipanasin ulang",
            "Jadi nol, patinya udah nggak kehitung",
        ],
        0,
        "Ada sedikit perubahan pati yang bikin sebagian nggak kecerna, tapi bedanya kecil dan nggak konsisten. Porsinya tetep yang nentuin, bukan suhunya.",
    ),
    (
        "dq-050",
        "serat",
        "Makan siang kamu sekitar 800 kalori, tapi jam 3 udah laper. Paling mungkin karena?",
        [
            "Isinya nasi dan gorengan, minim protein dan serat",
            "Kalorinya masih kurang, harusnya sekitar 1.200",
            "Metabolisme kamu kecepetan buat porsi segitu",
            "Kamu kurang minum air sebelum makan",
        ],
        0,
        "800 kalori itu banyak, jadi masalahnya bukan jumlahnya. Nasi plus gorengan bikin kalori masuk tinggi tapi kenyangnya pendek. Tambah lauk dan sayur, kalorinya bisa sama tapi tahannya beda.",
    ),
    (
        "dq-051",
        "serat",
        "Sepotong mangga sekitar 60 kalori, segelas jus mangga kemasan sekitar 200. Buat yang mau turun berat?",
        [
            "Buahnya jalan terus, jusnya yang diatur",
            "Dua-duanya dihindari, gulanya sama",
            "Jusnya lebih baik karena lebih cepat dicerna",
            "Mangga dihindari karena bikin diabetes",
        ],
        0,
        "Gula buah datang bareng serat dan air, dan hampir nggak ada orang gendut gara-gara kebanyakan mangga. Yang jadi masalah biasanya bentuk cairnya: gulanya tinggi, kenyangnya nol.",
    ),
    (
        "dq-052",
        "serat",
        "Di warteg, tanpa nimbang apa-apa, pola piring yang paling gampang dipegang?",
        [
            "Separuh sayur, seperempat lauk protein, seperempat nasi",
            "Nasinya banyak, lauknya sedikit, biar hemat dan kenyang",
            "Cuma lauk, nasinya dilepas total",
            "Separuh nasi, separuh gorengan",
        ],
        0,
        "Aturan yang bisa dipakai di warteg, di rumah dan di kondangan tanpa aplikasi. Lepas nasi total biasanya nggak tahan lama, dan separuh piring gorengan itu yang kalorinya paling tinggi dari empat pilihan ini.",
    ),
    (
        "dq-053",
        "serat",
        "Mana kebiasaan makan kita yang udah bener dan paling gampang ditambah?",
        [
            "Lalapan dan sayur mentah di warung",
            "Kerupuk di tiap kali makan",
            "Kuah santan diminum sampai habis",
            "Teh manis sebagai pendamping",
        ],
        0,
        "Lalapan itu serat dan volume yang hampir nol kalori, dan biasanya gratis kalau minta lebih. Tiga lainnya juga kebiasaan kita, tapi nambah kalori tanpa nambah kenyang.",
    ),
    (
        "dq-054",
        "serat",
        "Kamu baru nambah protein banyak dan jadi sembelit. Langkah pertama?",
        [
            "Tambah air dan sayur, proteinnya jangan dikurangi",
            "Berhenti makan protein sampai lancar lagi",
            "Langsung beli obat pencahar di apotek",
            "Kurangi sayurnya, karena serat bikin makin keras",
        ],
        0,
        "Yang biasanya kurang itu serat dan air, bukan proteinnya yang salah. Nambah lauk sering bikin sayur kegeser dari piring, dan itu yang bikin macet.",
    ),
    # --- latihan beban dan otot -------------------------------------------
    (
        "dq-055",
        "otot",
        "Empat orang latihan 3 bulan. Siapa yang ototnya paling nambah?",
        [
            "Yang bebannya naik pelan-pelan tiap 2 minggu",
            "Yang paling banyak keringetnya",
            "Yang paling banyak variasi gerakannya",
            "Yang paling lengkap suplemennya",
        ],
        0,
        "Otot nambah karena badan dipaksa ngadepin beban yang makin berat, namanya progressive overload. Tanpa itu, keringat, variasi dan suplemen nggak ngasih alasan buat berubah.",
    ),
    (
        "dq-056",
        "otot",
        "Kamu cuma bisa 2 hari seminggu tapi konsisten. Temanmu niat 6 hari, biasanya berhenti di minggu ketiga. Setahun lagi?",
        [
            "Kamu yang lebih maju, dan bedanya jauh",
            "Temanmu, karena programnya lebih berat",
            "Sama aja",
            "Dua-duanya nggak nambah apa-apa",
        ],
        0,
        "Dua kali seminggu selama setahun itu sekitar 100 sesi. Enam kali seminggu yang tahan tiga minggu itu 18 sesi, terus nol. Yang nentuin bukan program terbaik, tapi program yang beneran kamu jalanin.",
    ),
    (
        "dq-057",
        "otot",
        "Temanmu berhenti latihan 6 bulan dan badannya jadi lembek. Yang beneran kejadian?",
        [
            "Ototnya nyusut, lemaknya nambah",
            "Ototnya berubah jadi lemak, makanya jadi lembek",
            "Ototnya pindah ke perut dan pinggang",
            "Lemaknya berubah jadi otot yang lembek",
        ],
        0,
        "Otot dan lemak itu dua jaringan beda dan nggak bisa berubah jadi satu sama lain, sama kayak besi nggak bisa jadi kayu. Hasilnya kelihatan sama, tapi paham bedanya bikin kamu tahu harus ngapain: latihan buat ototnya, makan buat lemaknya.",
    ),
    (
        "dq-058",
        "otot",
        "Latihan A bikin kamu pegel 2 hari. Latihan B nggak bikin pegel tapi bebannya naik. Mana yang lebih berhasil?",
        [
            "B, karena bebannya naik",
            "A, pegel tandanya berhasil",
            "A, karena ototnya kerja lebih keras",
            "Nggak bisa dibandingin",
        ],
        0,
        "Pegel bisa muncul cuma karena gerakannya baru atau lama nggak dipakai, dan bisa hilang justru waktu kamu makin kuat. Ukuran yang kepake itu beban dan repetisi yang naik, dicatat, bukan rasanya besok pagi.",
    ),
    (
        "dq-059",
        "otot",
        "Cewek latihan beban rutin 6 bulan, makannya normal. Hasil yang paling mungkin?",
        [
            "Lebih kuat dan bentuknya lebih padat",
            "Gede kayak binaragawan yang di foto-foto",
            "Nggak ada perubahan yang kelihatan sama sekali",
            "Kuat doang, bentuk ototnya nggak ikut berubah",
        ],
        0,
        "Badan besar itu proyek bertahun-tahun yang disengaja plus makan banyak, bukan efek samping latihan biasa. Yang datang dulu itu kekuatan dan bentuk yang lebih padat.",
    ),
    (
        "dq-060",
        "otot",
        "Buat latihan kekuatan, istirahat antar set 30 detik dibanding 2 menit?",
        [
            "Yang 2 menit bikin set berikutnya lebih kuat",
            "Yang 30 detik lebih bagus karena jantungnya ikut kelatih",
            "Sama aja, yang penting jumlah setnya",
            "Yang 30 detik bikin otot lebih cepat gede",
        ],
        0,
        "Istirahat yang cukup itu yang bikin set kedua dan ketiga masih berat betul. Kalau kependekan, bebannya turun sendiri dan yang kelatih malah napas, bukan kekuatan.",
    ),
    (
        "dq-061",
        "otot",
        "6 bulan kamu rutin datang, tapi bebannya nggak pernah naik. Paling mungkin?",
        [
            "Rutinnya jalan, tapi perkembangannya udah berhenti",
            "Ototnya tetep nambah, yang penting rutin",
            "Itu cara paling aman jadi paling bagus",
            "Bebannya nggak penting, yang penting kamu hadir terus",
        ],
        0,
        "Rutin itu syaratnya, bukan tujuannya. Badan udah kenal beban itu dan nggak punya alasan berubah lagi. Naikin sedikit tiap satu dua minggu, atau tambah repetisi dulu kalau bebannya belum bisa naik.",
    ),
    (
        "dq-062",
        "otot",
        "Selain kelihatan lebih bagus, nambah otot paling ngebantu apa?",
        [
            "Gula darah, tulang, dan kekuatan sehari-hari",
            "Cuma penampilan, sisanya bonus",
            "Cuma penting buat atlet dan binaragawan",
            "Bikin kamu harus minum suplemen terus-terusan",
        ],
        0,
        "Otot itu tempat gula darah dipakai, jadi nambah otot bikin badan lebih tahan diabetes tipe 2. Tulang ikut kuat karena kena beban, dan angkat barang atau bangun dari kursi jadi ringan.",
    ),
    (
        "dq-063",
        "otot",
        "Umur 50 baru mulai latihan beban. Dibanding orang 25 yang mulai di hari yang sama, siapa yang untungnya paling besar?",
        [
            "Yang 50, karena dia ngerem penurunan yang udah jalan",
            "Yang 25, yang 50 udah telat",
            "Sama aja",
            "Nggak ada yang untung, umur 50 bahaya angkat beban",
        ],
        0,
        "Dari umur 30-an otot dan tulang turun sendiri kalau nggak dilatih. Yang 25 nambah di atas puncaknya, yang 50 ngerem yang udah mulai hilang, dan itu bedanya antara mandiri atau nggak di umur 70.",
    ),
    (
        "dq-064",
        "otot",
        "Pemula, minggu pertama. Mana yang paling nentuin hasil 2 tahun ke depan?",
        [
            "Teknik yang rapi, bebannya nyusul",
            "Beban seberat mungkin dari awal",
            "Suplemen dari hari pertama",
            "Jumlah gerakan sebanyak mungkin",
        ],
        0,
        "Teknik rapi bikin kamu bisa naik beban bertahun-tahun tanpa berhenti gara-gara cedera. Beban berat dengan teknik jelek biasanya berakhir di jeda dua bulan, dan jeda itu yang ngabisin hasil.",
    ),
    # --- kardio ------------------------------------------------------------
    (
        "dq-065",
        "kardio",
        "Setelah 3 bulan kardio rutin, denyut jantung istirahat kamu turun dari 78 ke 66. Artinya?",
        [
            "Jantungnya mompa lebih banyak per denyut",
            "Jantungnya jadi lemah",
            "Kamu kurang tidur",
            "Nggak ada artinya, angka itu naik turun sendiri",
        ],
        0,
        "Jantung yang terlatih ngirim darah lebih banyak sekali denyut, jadi butuh denyut lebih sedikit buat kerjaan yang sama. Itu salah satu tanda kebugaran yang paling gampang dicek sendiri.",
    ),
    (
        "dq-066",
        "kardio",
        "Anjuran kardio sedang sekitar 150 menit seminggu. Kamu jalan cepat 25 menit, 4 hari. Kurang berapa?",
        ["Sekitar 50 menit", "Udah lewat", "Sekitar 20 menit", "Sekitar 100 menit"],
        0,
        "25 kali 4 itu 100 menit, jadi kurang sekitar 50. Bisa ditutup dengan nambah satu hari lagi, atau nambah 10 menit di tiap hari yang udah jalan.",
    ),
    (
        "dq-067",
        "kardio",
        "Kamu jalan cepat 30 menit tiap hari, tapi nggak pernah kardio di gym. Kardio mingguan kamu?",
        [
            "Udah di atas anjuran, dan itu beneran ngitung",
            "Nol, jalan nggak dihitung olahraga",
            "Baru sekitar separuh dari yang dibutuhin seminggu",
            "Cuma ngitung kalau di treadmill",
        ],
        0,
        "30 menit kali 7 hari itu 210 menit, di atas anjuran 150. Kardio yang beneran kamu lakuin tiap hari ngalahin program lari yang cuma jadi rencana.",
    ),
    (
        "dq-068",
        "kardio",
        "Dua orang turun 6 kg. A cuma kardio, B kardio plus latihan beban. Bedanya di badan?",
        [
            "A kehilangan lebih banyak otot, jadi ringan tapi lembek",
            "Sama aja, yang penting angka di timbangannya turun",
            "B turunnya nggak beneran karena ototnya ikut nambah",
            "A ototnya nambah sendiri dari kardionya",
        ],
        0,
        "Tanpa latihan beban, badan nggak punya alasan nahan otot waktu kalorinya kurang. Hasilnya lebih ringan tapi bentuknya nggak berubah banyak, dan lebih gampang balik karena otot yang hilang bikin kalori harian ikut turun.",
    ),
    (
        "dq-069",
        "kardio",
        "Kamu sekarang 3.000 langkah sehari. Target yang paling masuk akal buat bulan ini?",
        [
            "Sekitar 5.000 sampai 6.000, naik pelan",
            "Langsung 10.000 mulai besok",
            "Tetep 3.000, yang penting latihan beban",
            "20.000, biar cepat kelihatan",
        ],
        0,
        "Manfaatnya udah kelihatan dari sekitar 7.000, tapi lompat dari 3.000 ke 10.000 biasanya tahan seminggu. Naik 2.000 dulu, tahan sebulan, baru naik lagi.",
    ),
    (
        "dq-070",
        "kardio",
        "Jalan santai 30 menit: 100 kalori, 60% dari lemak. Jalan cepat 30 menit: 200 kalori, 40% dari lemak. Mana yang lemaknya lebih banyak kebakar?",
        [
            "Yang cepat: 80 kalori dari lemak lawan 60",
            "Yang santai, karena persentasenya lebih tinggi",
            "Sama",
            "Nggak ada, dua-duanya cuma bakar gula",
        ],
        0,
        "Persentase besar dari total yang kecil tetep kecil: 60% dari 100 itu 60, 40% dari 200 itu 80. Itu kenapa 'fat burning zone' nyesatin, dan kenapa yang dihitung total kalorinya.",
    ),
    (
        "dq-071",
        "kardio",
        "Naik tangga 4 lantai, 2 kali sehari, 20 hari kerja. Sebulan itu?",
        [
            "160 lantai, gratis dan tanpa nambah jadwal",
            "Nggak ada efeknya karena cuma beberapa menit",
            "Terlalu banyak, lututnya bisa rusak",
            "Sama capeknya sama lari 10 km",
        ],
        0,
        "4 kali 2 kali 20 itu 160 lantai sebulan tanpa nambah jadwal apa pun. Gerakan kecil yang diulang tiap hari nambahnya banyak, dan lutut yang sehat justru makin kuat kalau dipakai.",
    ),
    (
        "dq-072",
        "kardio",
        "Latihan beban 45 menit, bebannya naik dari minggu lalu, tapi kamu hampir nggak keringetan. Sesinya?",
        [
            "Berhasil, keringat bukan ukurannya",
            "Sia-sia, harus basah dulu baru kerja",
            "Cuma setengah berhasil",
            "Salah program",
        ],
        0,
        "Keringat itu cara badan mendinginkan diri, dipengaruhi cuaca dan kipas, bukan meteran kerja. Yang ngukur itu bebannya naik atau nggak, dan itu ada di catatan latihanmu.",
    ),
    (
        "dq-073",
        "kardio",
        "Sehari cuma ada 1 jam, mau beban dan kardio, prioritasnya nambah otot. Urutannya?",
        [
            "Beban dulu, kardio santai setelahnya",
            "Kardio 40 menit dulu sampai capek, beban sisanya",
            "Nggak boleh dua-duanya di hari yang sama",
            "Bebannya diganti kardio aja biar hemat waktu",
        ],
        0,
        "Yang lebih penting dikerjain waktu tenaga masih penuh. Kardio berat duluan bikin bebannya turun, dan beban yang turun berarti sinyal buat ototnya ikut turun.",
    ),
    (
        "dq-074",
        "kardio",
        "Naik 2 lantai udah ngos-ngosan. Kabar baiknya?",
        [
            "Ini yang paling cepat berubah, beberapa minggu udah kerasa",
            "Nggak ada, itu bawaan genetik dari orang tua",
            "Berarti yang kurang ototnya, bukan kardionya",
            "Berarti kamu harus mulai dari lari, jalan nggak cukup",
        ],
        0,
        "Kebugaran kardio itu yang paling cepat naik, dan juga paling cepat turun kalau ditinggal. Beberapa minggu jalan cepat rutin biasanya udah kelihatan di tangga yang sama.",
    ),
    # --- tidur, stres, pemulihan ------------------------------------------
    (
        "dq-075",
        "pemulihan",
        "Latihan berat Senin, terus tidurnya cuma 5 jam di Senin dan Selasa. Hasil latihan Senin?",
        [
            "Nggak kepake penuh, karena perbaikannya kejadian waktu tidur",
            "Tetep penuh, yang penting latihan beratnya udah dijalanin",
            "Malah lebih bagus, badan dipaksa adaptasi",
            "Nggak ngaruh, tidur cuma buat ngilangin capek",
        ],
        0,
        "Latihan itu sinyalnya, tidur itu waktu kerjanya. Kurang tidur bikin perbaikan otot melambat dan angkatan besok ikut turun, jadi sesi yang bagus bisa kebuang gara-gara dua malam.",
    ),
    (
        "dq-076",
        "pemulihan",
        "Seminggu penuh kamu tidur 5 jam. Yang paling mungkin kamu rasain?",
        [
            "Lebih laper, terutama ke yang manis, dan angkatan turun",
            "Lemak lebih cepat hilang karena bangunnya lebih lama",
            "Nggak ada bedanya asal kopinya cukup",
            "Otot nambah lebih cepat",
        ],
        0,
        "Kurang tidur ngacak hormon lapar dan bikin tenaga turun, jadi dua-duanya lawan dari yang kamu mau. Bangun lebih lama nggak nutup itu, karena yang nambah biasanya makannya.",
    ),
    (
        "dq-077",
        "pemulihan",
        "Kamu udah latihan rutin dan makan lumayan, tapi tidurnya 5 jam. Satu perubahan yang paling ngefek?",
        [
            "Nambah tidur jadi 7 jam",
            "Nambah suplemen",
            "Nambah satu hari latihan",
            "Ngurangin kalori lagi",
        ],
        0,
        "Kalau tidurnya 5 jam, itu bagian yang paling ketinggalan, dan nambah satu dua jam biasanya lebih ngefek daripada nambah apa pun ke program. Nambah latihan waktu tidurnya kurang malah nambah lubangnya.",
    ),
    (
        "dq-078",
        "pemulihan",
        "Kamu lagi stres berat gara-gara kerjaan. Target program yang paling masuk akal?",
        [
            "Turunin jadi yang dasar: 2 kali latihan dan tidur cukup",
            "Naikin latihannya biar stresnya cepat hilang",
            "Berhenti dulu total sampai keadaannya tenang",
            "Ganti ke diet paling ketat biar ada yang bisa dipegang",
        ],
        0,
        "Stres nambah nafsu makan dan ngurangin tidur, jadi ini waktu yang salah buat target ambisius. Nahan kebiasaan dasar bikin kamu nggak mulai dari nol lagi bulan depan.",
    ),
    (
        "dq-079",
        "pemulihan",
        "Program 4 hari latihan, 3 hari istirahat. Hari istirahatnya?",
        [
            "Bagian dari programnya, di situ badannya berubah",
            "Bagian yang bisa dilepas kalau lagi rajin",
            "Tanda programnya kurang berat",
            "Cuma buat atlet",
        ],
        0,
        "Badan berkembang di antara latihan, bukan waktu latihan. Ngisi hari istirahat dengan latihan berat lagi itu nambah sinyal tanpa nambah waktu buat ngerjainnya.",
    ),
    (
        "dq-080",
        "pemulihan",
        "Pemula latihan berat 7 hari seminggu dari minggu pertama. Yang paling sering kejadian?",
        [
            "Berhenti di bulan pertama, capek berlebihan atau cedera",
            "Hasilnya paling cepat dibanding yang lain",
            "Kebiasaannya jadi yang paling kuat",
            "Nggak ada risiko selama makannya cukup, badan nyesuain sendiri",
        ],
        0,
        "Yang paling sering bikin orang berhenti bukan malas, tapi cedera atau capek berlebihan di bulan pertama. Program yang selamat setahun ngalahin program bagus yang tahan tiga minggu.",
    ),
    (
        "dq-081",
        "pemulihan",
        "Kopi sebelum latihan. Mana yang paling tepat?",
        [
            "Bisa ngebantu fokus dan tenaga",
            "Bikin dehidrasi parah, jangan sebelum latihan",
            "Nggak ada efeknya, cuma perasaan",
            "Makin banyak gelasnya makin kuat",
        ],
        0,
        "Kafein salah satu yang efeknya beneran kelihatan di penelitian, dan cukup satu gelas. Yang bikin rugi biasanya bukan kafeinnya, tapi 250 kalori gula yang nempel di gelasnya.",
    ),
    (
        "dq-082",
        "pemulihan",
        "Tidur cuma 4 jam, dan hari ini jadwal latihan berat. Pilihan paling masuk akal?",
        [
            "Latihan ringan aja hari ini, yang beratnya digeser",
            "Tetep latihan berat, jangan lembek",
            "Kopi 3 gelas biar kuat",
            "Berhenti latihan seminggu buat balikin tidur",
        ],
        0,
        "Latihan berat dengan tidur 4 jam itu risiko cedera naik dan hasilnya jelek. Digeser, bukan dihapus: program setahun nggak rusak karena satu hari, tapi rusak kalau tiap capek kamu berhenti seminggu.",
    ),
    # --- suplemen dan mitos ------------------------------------------------
    (
        "dq-083",
        "mitos",
        "Uang suplemen cuma cukup buat satu. Mana yang paling banyak buktinya buat kekuatan dan otot?",
        ["Kreatin", "BCAA", "Fat burner", "Multivitamin yang paling mahal"],
        0,
        "Kreatin murah, paling banyak diteliti, dan aman buat orang sehat. Tetep nomor dua setelah latihan dan makan: suplemen nambah beberapa persen di atas yang udah jalan, bukan gantinya.",
    ),
    (
        "dq-084",
        "mitos",
        "Fat burner harganya 300 ribu sebulan. Kalau efeknya beneran ada, kira-kira setara apa?",
        [
            "Beberapa puluh kalori sehari",
            "Sekitar 500 kalori sehari",
            "Sekitar 1 kg lemak seminggu",
            "Bebas nggak usah atur makan lagi",
        ],
        0,
        "Efek yang paling bagus di penelitian pun kecil, sementara segelas kopi susu gula aren itu 250 kalori. Uangnya lebih ngefek dipakai buat telur, ikan dan sayur.",
    ),
    (
        "dq-085",
        "mitos",
        "Teh detox bikin timbangan turun 2 kg dalam 3 hari. Kalau itu beneran lemak, kamu harus kekurangan?",
        [
            "Sekitar 15.000 kalori, yang nggak mungkin",
            "Sekitar 2.000 kalori dalam 3 hari",
            "Sekitar 5.000 kalori dalam 3 hari",
            "Nggak butuh kekurangan kalori, teh detoxnya yang kerja",
        ],
        0,
        "1 kg lemak sekitar 7.700 kalori, jadi 2 kg itu sekitar 15.000, atau 5.000 sehari. Nggak ada orang yang bisa. Yang turun itu air dan isi perut, dan balik dalam beberapa hari.",
    ),
    (
        "dq-086",
        "mitos",
        "Setelah latihan timbangan turun 1 kg, terus kamu minum 2 gelas air. Timbangannya?",
        [
            "Balik lagi hampir semuanya, karena yang hilang air",
            "Tetep turun, lemaknya udah kebakar",
            "Turun lagi, karena air bikin metabolisme naik",
            "Naik lebih tinggi dari sebelum latihan",
        ],
        0,
        "1 kg lemak butuh sekitar 7.700 kalori, dan nggak ada sesi latihan segitu. Yang keluar keringat, dan beratnya balik begitu kamu minum. Itu kenapa nimbang setelah latihan nggak ngasih info apa-apa.",
    ),
    (
        "dq-087",
        "mitos",
        "Kamu sit-up 200 kali sehari selama sebulan. Perutnya?",
        [
            "Otot perutnya lebih kuat, lemaknya masih di situ",
            "Lemak perutnya yang hilang duluan",
            "Nggak ada perubahan apa-apa sama sekali",
            "Lemaknya pindah ke bagian badan yang lain",
        ],
        0,
        "Nggak ada latihan yang bisa milih lokasi lemak. Sit-up nguatin otot di bawahnya, tapi yang bikin kelihatan itu lapisan lemaknya berkurang, dan itu urusan makan dan total latihan.",
    ),
    (
        "dq-088",
        "mitos",
        "Dua orang makan 2.000 kalori sehari. A makan terakhir jam 6, B jam 10 malam. Setelah sebulan?",
        [
            "Bedanya kecil, yang nentuin totalnya",
            "B naik berat badan, A turun",
            "B otomatis nyimpen lemak lebih banyak",
            "A yang naik, karena kelaperan malamnya",
        ],
        0,
        "Badan nggak punya jam yang bilang 'lewat jam 8 disimpen jadi lemak'. Makan malam telat baru jadi masalah kalau bikin porsinya nambah atau tidurnya keganggu, bukan karena jamnya.",
    ),
    (
        "dq-089",
        "mitos",
        "Kamu ganti 2 sendok gula pasir di teh jadi 2 sendok madu. Kalorinya?",
        [
            "Mirip, madu tetep gula",
            "Turun separuh, madu lebih ringan",
            "Jadi nol, madu bukan gula",
            "Naik dua kali dari gula pasir",
        ],
        0,
        "Madu ada sedikit mikronutrien, tapi kalorinya mirip gula pasir dan badan ngolahnya kurang lebih sama. Kalau tujuannya ngurangin gula, yang perlu turun jumlahnya, bukan jenisnya.",
    ),
    (
        "dq-090",
        "mitos",
        "Makan kamu udah macam-macam: sayur, buah, telur, ikan, tempe. Multivitamin harian?",
        [
            "Biasanya nggak perlu",
            "Wajib, makanan sekarang udah nggak ada gizinya",
            "Wajib kalau kamu latihan",
            "Bikin gendut",
        ],
        0,
        "Kalau makanmu udah beragam, kekurangannya kecil dan multivitamin nggak ngasih tambahan yang kerasa. Beda cerita kalau ada kondisi khusus atau pilihan makanmu terbatas, itu tanya dokter.",
    ),
    # --- makanan sini, hitungan warung, puasa ------------------------------
    (
        "dq-091",
        "warung",
        "Batagor seporsi sekitar 450 kalori. Kamu makan itu jam 4 sebagai cemilan, dan makan malamnya tetep penuh. Hari itu?",
        [
            "Kelebihan seporsi makan besar, tanpa berasa makan besar",
            "Nggak masalah, cemilan nggak dihitung",
            "Impas, karena cemilan bikin makan malamnya lebih sedikit",
            "Masih kurang, karena batagor isinya ikan",
        ],
        0,
        "450 kalori itu setara sepiring nasi dengan lauk. Cemilan yang segede makan besar tapi nggak dianggap makan besar itu jalur paling sering bikin berat naik pelan-pelan.",
    ),
    (
        "dq-092",
        "warung",
        "Semangkok mie kocok sekitar 450 kalori. Ditambah nasi seporsi dan 5 keping kerupuk?",
        [
            "Sekitar 850",
            "Sekitar 550",
            "Sekitar 500",
            "Sekitar 1.500",
        ],
        0,
        "Nasi seporsi sekitar 260 dan 5 keping kerupuk sekitar 150, jadi totalnya sekitar 850 dalam sekali duduk. Mie plus nasi itu karbo dua kali, dan yang kurang biasanya protein dan sayurnya.",
    ),
    (
        "dq-093",
        "warung",
        "Seblak level 10 dibanding level 0, porsi dan isinya sama. Kalorinya?",
        [
            "Sama, pedes nggak nambah dan nggak ngurangin kalori",
            "Level 10 lebih rendah karena pedes bakar kalori",
            "Level 10 lebih tinggi karena bumbunya lebih banyak",
            "Level 0 lebih rendah karena nggak ada cabenya",
        ],
        0,
        "Pedes bikin keringetan dan jantung deg-degan, tapi itu bukan kalori kebakar. Yang bikin seblak tinggi itu kerupuk dan minyaknya, dan itu sama di level berapa pun.",
    ),
    (
        "dq-094",
        "warung",
        "Gado-gado udah termasuk seimbang. Kalau mau bikin lebih pas lagi?",
        [
            "Bumbu kacang dan kerupuknya dikurangi",
            "Tahu dan tempenya yang dikurangi",
            "Sayurnya dikurangi biar nggak kembung",
            "Lontongnya ditambah biar lebih kenyang",
        ],
        0,
        "Protein di gado-gado datang dari tahu, tempe, telur dan bumbu kacangnya, jadi itu bagian yang jangan disentuh. Yang bikin kalorinya bengkak biasanya bumbu yang kebanyakan dan kerupuknya.",
    ),
    (
        "dq-095",
        "warung",
        "Nasi padang, tapi mau lebih terkontrol. Mana yang paling ngefek?",
        [
            "Lauk yang dibakar, dan kuah santannya jangan banyak",
            "Nasinya dikurangi separuh, yang lain tetep sama",
            "Cuma rendangnya, nasinya dilepas total",
            "Hindari total, cari warung yang lain",
        ],
        0,
        "Kuah santan dan lauk goreng yang paling nambah, jadi itu tuas yang paling gede. Ngurangin nasi separuh ngirit sekitar 130 kalori, sementara kuah yang disiram penuh bisa nambah 300 lebih.",
    ),
    (
        "dq-096",
        "warung",
        "Bubur ayam plus kerupuk plus cakwe plus telur. Mana yang paling nambah kalori tanpa nambah kenyang?",
        [
            "Kerupuk dan cakwenya",
            "Bubur dan ayamnya",
            "Ayam dan telurnya",
            "Telur dan buburnya",
        ],
        0,
        "Dua-duanya digoreng: kalorinya masuk, kenyangnya nggak. Buburnya sendiri porsi karbo yang lumayan terkontrol, dan ayam plus telur itu bagian yang bikin kamu tahan sampai siang.",
    ),
    (
        "dq-097",
        "warung",
        "Es campur isinya buah, kelapa, kental manis dan sirup. Mana yang paling nambah kalori?",
        [
            "Kental manis dan sirupnya",
            "Buah dan kelapanya",
            "Kelapa dan es batunya",
            "Es batu dan buahnya",
        ],
        0,
        "Buah dan kelapa nambah sedikit, es batu nol. Kental manis dan sirup bisa nambah 200 kalori lebih dalam satu gelas, dan itu bagian yang paling gampang diminta dikurangi.",
    ),
    (
        "dq-098",
        "warung",
        "Puasa, tapi mau tetep latihan beban. Waktu yang paling masuk akal?",
        [
            "Sekitar sejam sebelum buka, atau setelah buka",
            "Tengah hari, biar lemaknya kebakar lebih banyak",
            "Subuh setelah sahur, terus tidur",
            "Nggak latihan sama sekali sebulan",
        ],
        0,
        "Dekat buka berarti kamu bisa langsung minum dan makan setelahnya, jadi cairan dan proteinnya nggak nunggu berjam-jam. Berhenti total sebulan bikin mulai lagi jadi berat, dan itu kerugian paling gede.",
    ),
    (
        "dq-099",
        "warung",
        "Sahur mana yang paling bikin tahan sampai sore?",
        [
            "Nasi secukupnya, telur, tempe dan sayur",
            "Nasi banyak plus kerupuk dan sambal",
            "Kopi manis, roti manis, sama gorengan",
            "Nasi plus mie instan dan kerupuk",
        ],
        0,
        "Protein dan serat yang bikin kenyangnya panjang, karbo doang bikin jam 10 udah lemes. Porsi besar tanpa lauk nggak nolong, karena yang nahan bukan banyaknya.",
    ),
    (
        "dq-100",
        "warung",
        "Kopi susu gula aren sekitar 250 kalori, latihan sejam sekitar 300. Kamu minum 2 gelas sehari dan latihan 3 kali seminggu. Seminggu?",
        [
            "Minumannya 3.500 kalori, latihannya 900",
            "Impas, kira-kira sama besar",
            "Latihannya masih menang tipis",
            "Nggak bisa dibandingin, beda urusan",
        ],
        0,
        "3.500 lawan 900 dalam seminggu. Bukan berarti latihan nggak berguna: latihan ngasih otot dan kesehatan yang nggak bisa didapet dari ngurangin minuman. Tapi buat berat badan, minumannya yang harus digarap.",
    ),
    # --- umur panjang vs sehat (bab 10) -----------------------------------
    (
        "dq-101",
        "umur",
        "Umur harapan hidup di Indonesia sekitar 70 tahun, tapi \"tahun sehatnya\" sekitar 62. Artinya?",
        [
            "Rata-rata ada sekitar 8 tahun terakhir yang dijalani dengan badan yang udah susah dipakai",
            "Rata-rata orang Indonesia meninggal di umur 62",
            "Rata-rata orang sakit-sakitan sepanjang hidupnya",
            "Angka itu nggak ada hubungannya sama kebiasaan sehari-hari",
        ],
        0,
        "Itu selisih antara umur panjang dan umur yang masih kepake. Kebiasaan latihan, makan dan tidur paling ngaruh ke selisih ini, bukan ke angka 70-nya.",
    ),
    (
        "dq-102",
        "umur",
        "Massa otot turun kira-kira 5% per dekade setelah umur 30 kalau nggak dilatih. Umur 70, sisa berapa persen dari puncaknya?",
        ["Sekitar 95%", "Sekitar 80%", "Sekitar 50%", "Sekitar 20%"],
        1,
        "Empat dekade dikali kira-kira 5% itu sekitar 20% yang hilang, jadi sisanya sekitar 80%. Kelihatan kecil per dekade, gede kalau ditumpuk.",
    ),
    (
        "dq-103",
        "umur",
        "Semua ini bagus buat jangka panjang. Mana yang paling susah dikejar kalau kamu tunda 20 tahun?",
        [
            "Bangun massa otot dan kepadatan tulang",
            "Berhenti merokok",
            "Ngurangin gula",
            "Tidur lebih cukup",
        ],
        0,
        "Tiga lainnya bisa kamu perbaiki kapan aja dan hasilnya langsung kerasa. Puncak otot dan tulang punya jendela waktu yang nutup sekitar umur 30, dan itu nggak bisa diulang.",
    ),
    (
        "dq-104",
        "umur",
        "Kenapa patah tulang panggul di umur 70 sering jadi awal kemunduran besar, bukan cuma cedera biasa?",
        [
            "Berbulan-bulan nggak bisa gerak bikin otot dan kebugaran hilang cepat",
            "Tulang panggul nggak bisa nyambung lagi",
            "Operasinya selalu gagal di umur segitu",
            "Karena bikin tulang lain ikut patah",
        ],
        0,
        "Tulangnya biasanya bisa diperbaiki. Yang susah dibalikin itu otot dan kebugaran yang hilang selama berbaring, dan dari situ banyak orang nggak balik mandiri lagi.",
    ),
    (
        "dq-105",
        "umur",
        "Umur 60 kamu butuh waktu lebih lama buat inget nama orang dibanding umur 25. Itu?",
        [
            "Normal: kecepatan prosesnya turun, tapi kosakata dan pengalaman sering nambah",
            "Tanda awal pikun",
            "Tanda kurang tidur, bukan umur",
            "Bisa dicegah total kalau minum suplemen otak",
        ],
        0,
        "Otak yang menua jadi lebih pelan, bukan otomatis lebih jelek. Pikun itu penyakit, bukan jadwal yang pasti datang.",
    ),
    (
        "dq-106",
        "umur",
        "Dua orang umur 60. A masih bisa naik 3 lantai sambil ngobrol, B udah ngos-ngosan di lantai satu. Bedanya paling besar datang dari?",
        [
            "Puluhan tahun kebiasaan gerak",
            "Genetik jantung mereka",
            "Selisih umur beberapa bulan",
            "Berat badan doang",
        ],
        0,
        "Genetik dan berat badan ikut ngaruh, tapi yang bikin bedanya sebesar itu biasanya puluhan tahun kebiasaan. Ini juga kabar baiknya: bagian itu yang kamu pegang.",
    ),
    (
        "dq-107",
        "umur",
        "Kebutuhan protein per kilo berat badan buat orang tua dibanding orang muda?",
        [
            "Cenderung lebih banyak, karena badannya kurang responsif ke protein",
            "Lebih sedikit, karena ototnya lebih kecil",
            "Sama aja",
            "Nggak perlu protein lagi",
        ],
        0,
        "Ini yang sering kebalik. Badan yang menua butuh dorongan lebih besar buat bikin otot dari protein yang sama, jadi anjurannya biasanya lebih tinggi, bukan lebih rendah.",
    ),
    (
        "dq-108",
        "umur",
        "Berat 60 kg, target 1,6 gram protein per kilo. Sarapan 2 telur (13 g), makan siang sepotong ayam (25 g). Kira-kira masih kurang berapa?",
        ["Sekitar 60 gram", "Sekitar 20 gram", "Sekitar 40 gram", "Udah cukup"],
        0,
        "Targetnya sekitar 96 gram, yang masuk baru sekitar 38. Sisanya sekitar 58 gram, jadi makan malam dan cemilan masih harus kerja keras.",
    ),
    (
        "dq-109",
        "umur",
        "Setelah menopause, kepadatan tulang perempuan turun lebih cepat. Mana yang paling ngebantu?",
        [
            "Latihan beban, protein cukup, plus kalsium dan vitamin D",
            "Istirahat lebih banyak biar tulangnya nggak kena beban",
            "Kardio ringan aja, hindari angkat berat",
            "Suplemen kolagen tiap hari",
        ],
        0,
        "Tulang jadi lebih kuat justru karena dibebani. Menghindari beban itu kebalikan dari yang dibutuhin, dan ini termasuk kesalahan yang paling mahal.",
    ),
    (
        "dq-110",
        "umur",
        "A mulai latihan beban umur 25 dan konsisten. B baru mulai umur 55. Umur 70, siapa yang lebih kuat?",
        [
            "A, dan bedanya biasanya lumayan besar",
            "B, karena latihannya lebih baru",
            "Sama, di umur 70 semua orang sama",
            "B, karena A pasti udah cedera-cederaan",
        ],
        0,
        "A mulai dari puncak yang lebih tinggi dan penurunannya lebih datar. Tapi jangan salah baca: B yang mulai umur 55 tetep jauh lebih kuat daripada B yang nggak pernah mulai.",
    ),
    (
        "dq-111",
        "umur",
        "Kenapa gula darah yang sering tinggi bertahun-tahun jadi masalah besar di umur tua?",
        [
            "Merusak pembuluh darah kecil, termasuk di mata, ginjal dan saraf",
            "Cuma bikin gigi rusak",
            "Cuma bikin ngantuk",
            "Nggak masalah selama berat badan normal",
        ],
        0,
        "Kerusakannya pelan dan nggak kerasa sampai udah lanjut. Latihan beban ngebantu di sini juga, karena otot itu tempat gula darah dipakai.",
    ),
    (
        "dq-112",
        "umur",
        "Tidur 4 jam Senin sampai Jumat, terus 12 jam di hari Sabtu. Itu?",
        [
            "Sebagian bisa kekejar, tapi performa dan nafsu makan udah keganggu seminggu penuh",
            "Impas, totalnya sama aja",
            "Lebih bagus daripada 7 jam tiap hari",
            "Nggak ada bedanya sama sekali",
        ],
        0,
        "Tidur panjang di akhir minggu ngebantu, tapi nggak ngebalikin lima hari angkatan yang jelek dan nafsu makan yang naik. Yang rutin tiap malam menang.",
    ),
    (
        "dq-113",
        "umur",
        "Kalau cuma bisa milih SATU kebiasaan buat dijalanin 30 tahun ke depan, mana yang paling ngejaga kemandirian di umur tua?",
        [
            "Latihan beban 2x seminggu",
            "Minum suplemen lengkap tiap hari",
            "Diet ketat tanpa karbo",
            "Cek darah lengkap tiap bulan",
        ],
        0,
        "Satu kebiasaan ini sekaligus jagain otot, tulang dan gula darah, tiga hal yang paling nentuin kamu masih bisa ngurus diri sendiri atau nggak.",
    ),
    (
        "dq-114",
        "umur",
        "Di umur 70, mana yang biasanya lebih cepat bikin nggak mandiri?",
        [
            "Kekurangan 5 kg otot",
            "Kelebihan 5 kg lemak",
            "Dua-duanya sama saja",
            "Nggak ada yang berpengaruh di umur segitu",
        ],
        0,
        "Bukan berarti lemak berlebih nggak masalah. Tapi di umur segitu, kehilangan otot itu yang paling cepat bikin susah bangun dari kursi dan gampang jatuh.",
    ),
    (
        "dq-115",
        "umur",
        "Ukuran paling jujur buat \"masih sehat\" di umur 65?",
        [
            "Masih bisa naik tangga, bangun dari kursi tanpa tangan, dan bawa barang sendiri",
            "Angka di timbangan",
            "Belum pernah masuk rumah sakit",
            "Orang tuanya umur panjang",
        ],
        0,
        "Yang nentuin kualitas hidup itu apa yang masih bisa kamu lakuin, bukan angka. Tiga gerakan itu juga yang paling gampang dilatih dari sekarang.",
    ),
]



# Which topic each question belongs to, for `nutrition/interleave.py`. The model
# has no topic column: nothing reads this at run time, because the order it
# produces is baked into `position` by a migration.
TOPIC_OF = {code: topic for code, topic, *_ in RAW}

TOPICS = sorted(set(TOPIC_OF.values()))


def _build(rows):
    """Turn the compact rows into what the model stores.

    The correct answer is moved to a slot derived from the question's code (see
    nutrition/shuffle.py). Written by hand, 77 of these 100 had the answer at B
    and none at C, so "always pick the middle one" scored 77% without reading.
    Write the answer wherever it reads best here; placement is handled for you.
    """
    letters = "abcdefgh"
    built = []
    for position, (code, _topic, question, choices, answer_index, explanation) in (
        enumerate(rows, start=1)
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
