# Aturan Kelas Baru: Pegangan buat Admin

Dikirim ke admin setelah deploy. Simpan, dibaca lagi kalau ada member nanya.
Bahasa Indonesia karena ini dibaca admin dan dipakai ngomong ke member.

---

Halo tim,

Aturan booking kelas udah berubah dan udah live di web. Ini rangkumannya, biar
kalau ada member nanya, jawabannya kita sama semua.

**Yang paling penting: kalau bingung, suruh buka link ini.**
mulaigym.id/kelas/aturan/
Semua aturannya ada di situ, lengkap sama contohnya. Nggak perlu login, jadi bisa
langsung di-share di WhatsApp. Kalau ada member komplain, kirim link ini dulu,
baru dijelasin kalau masih nanya.

---

## Kenapa diubah

Kelas makin penuh. Bulan Maret cuma keisi 29%, bulan Agustus udah 55%, dan kelas
sore (16:30, 17:15, 18:15, 19:00) hampir selalu penuh.

Masalahnya bukan cuma penuh, tapi tempatnya nggak kepakai:

1. Member booking 2 kelas sekaligus begitu jadwalnya keluar, biar nggak kehabisan.
2. Beberapa menit sebelum kelas, salah satunya dibatalin.
3. Yang di antrian naik jadi booking, tapi udah nggak sempet tau, jadi nggak dateng.
4. Akhirnya kelas yang harusnya 6 orang cuma keisi 4.

Ada kejadian nyata: 6 booking, 4 antri, yang dateng cuma 4 orang.

Jadi bukan soal member nakal. Sistemnya emang ngasih celah. Sekarang celahnya
ditutup.

---

## 3 aturan barunya

### 1. Sehari booking 1 kelas dulu

Dulu boleh langsung 2 kelas per hari. Sekarang 1 dulu.

Masih boleh ikut kelas kedua di hari yang sama, tapi bookingnya baru bisa
**1 jam sebelum kelas itu mulai**.

Contoh: kelas jam 19:00, tombol bookingnya buka jam 18:00.

Di web, tombolnya langsung nulis jam berapa dia buka, misal "Bisa jam 18:00".
Jadi kalau member bilang "kok nggak bisa booking", suruh liat tombolnya, jamnya
ada di situ.

**Kalau ditanya kenapa:** biar tempatnya kebagian dulu ke member yang belum
kelas sama sekali hari itu. Kalau tempat kedua dipegang seharian, yang belum
kebagian nggak pernah dapet.

### 2. Batalin paling lambat 4 jam sebelum kelas

Batalin lebih dari 4 jam sebelum kelas: **bebas**, mau berapa kali pun, nggak ada
catatan apa-apa. Ini yang kita mau member lakuin.

Batalin kurang dari 4 jam: **dihitung sama kayak nggak dateng**.

Contoh, kelas jam 17:15:
- Batalin jam 13:15 atau lebih awal, aman.
- Batalin jam 16:00, kena catatan.

Buat kelas pagi, ini artinya harus dibatalin malem sebelumnya. Kelas jam 07:15
batasnya jam 03:15. Emang berat, tapi kalau dibatalin jam 6 pagi, yang di antrian
udah nggak mungkin sempet siap-siap dan berangkat. Tempatnya kebuang juga.

Di web, tiap kelas yang lagi dipegang member selalu nulis jam batasnya, misal
"batalin sebelum jam 13:15". Sebelum mereka pencet Batalkan juga ada peringatan
dulu kalau udah lewat batas.

### 3. 3 kali buang tempat dalam 15 hari, booking kelas dikunci 3 hari

Ini aturan lama, cuma sekarang yang dihitung ada dua:
- Booking tapi nggak dateng
- Batalin kurang dari 4 jam sebelum kelas

Dihitung per hari. Sehari 2 kelas kelewat tetep dihitung 1.

Yang dikunci **cuma booking kelas**. Gym-nya tetep bisa dipakai kapan aja.
Setelah 3 hari, balik normal sendiri, nggak usah diapa-apain.

---

## Yang perlu diinget kalau ada yang komplain

**"Saya udah batalin kok, kenapa masih kena?"**
Karena batalinnya kurang dari 4 jam sebelum kelas. Tempatnya udah terlanjur
kebuang, temennya yang antri nggak sempet dapet kabar.

**"Kok nggak bisa booking 2 kelas?"**
Bisa, tapi kelas keduanya baru buka 1 jam sebelum mulai. Tombolnya ada jamnya.

**"Saya cuma dapet tempat mepet dari antrian, terus nggak bisa, kok saya kena?"**
Ini **nggak** kena. Kalau naik dari antrian pas udah lewat batas 4 jam, terus
batalin, sistemnya nggak ngitung. Kalau ada yang ngalamin dan tetep kena,
kabarin, itu bug.

**"Saya kena penalti tapi saya nggak tau aturannya."**
Kirim mulaigym.id/kelas/aturan/. Aturannya juga ada di halaman Akun Saya mereka,
lengkap sama daftar kelas mana aja yang kehitung.

**Kalau memang keadaannya wajar** (sakit, ada musibah, salah pencet), penaltinya
boleh dihapus manual. Caranya di bawah.

---

## Yang bisa diatur admin

Semua di **/admin**.

### Hapus penalti seseorang
Member > cari orangnya > kosongin kolom **Booking blocked until** > Simpan.
Langsung bisa booking lagi.

### Ubah angka aturannya
**Aturan & Penalti Kelas**. Semua angkanya di sini, dan yang di web langsung
ikut berubah, jadi nggak usah minta diubah ke developer:
- Berapa kelas per hari yang boleh dibooking jauh-jauh hari (sekarang 1)
- Berapa menit sebelum kelas, kelas tambahan buka (sekarang 60)
- Berapa jam batas batalin (sekarang 4)
- Berapa hari dihitung ke belakang (sekarang 15)
- Boleh buang tempat berapa kali (sekarang 2, jadi kena di kali ke-3)
- Dikunci berapa hari (sekarang 3)

Kalau ternyata kerasa terlalu ketat setelah jalan seminggu-dua minggu, kasih tau,
kita longgarin angkanya. Emang sengaja dibikin bisa diubah, biar nggak nunggu
update sistem.

### Tutup kelas di hari libur (BARU)
**Libur / Kelas Ditiadakan** > Tambah.
- Isi tanggal mulai dan selesai (kalau cuma sehari, isi sama)
- **Kelas**: kosongin kalau semua kelas libur. Isi salah satu kalau cuma satu
  kelas yang ditiadakan, misal trainer-nya cuti
- **Alasan**: ditulis apa adanya, ini dibaca member di halaman jadwal

Ini bisa diisi dari jauh-jauh hari, bahkan sebulan sebelumnya. Kelasnya jadi
nggak pernah dibuat, jadi nggak ada yang bisa booking, jadi nggak ada yang perlu
dikabarin satu-satu.

Kalau baru diisi pas kelasnya udah terlanjur dibuat, kelasnya tetep dibatalin
otomatis, dan yang udah booking masuk ke **Reminder** biar bisa dikabarin.

**Tolong dibiasain**: tiap tau ada tanggal libur, langsung isi di sini hari itu
juga. Ini yang bikin kita nggak perlu WA satu-satu lagi.

---

## Minggu pertama

Aturannya jalan mulai hari deploy, jadi minggu ini pasti ada yang kaget.

Yang paling ngebantu:
- Kalau ada yang nanya di depan, tunjukin langsung di HP-nya. Buka /kelas/, tunjuk
  tulisan "batalin sebelum jam sekian" di kelas dia. Sekali liat biasanya ngerti.
- Jangan mulai dari aturannya. Mulai dari: "biar temen kamu kebagian tempat".
  Itu yang nyambung.
- Minggu pertama, kalau ada yang kena karena nggak tau, hapus aja penaltinya.
  Kita lagi ngajarin, bukan ngehukum.
- Catat siapa aja yang komplain dan komplainnya apa. Kalau polanya sama, berarti
  ada yang kurang jelas di webnya, nanti kita betulin.

Makasih ya. Yang berat di awal ini kalian yang ngadepin, dan itu yang bikin
aturannya jalan.
