"""Homepage copy that needs data, or that is rendered in more than one place.

The FAQ is shown on the page and also handed to search engines as structured
data, so both read this one list and cannot say different things. The program
cards live here so the four of them are one loop, not four copies, and every
number-or-fallback phrase is written once in `claims()`.

No prices anywhere, on purpose: the gym would rather talk price in a chat, where
the admin can find the program that fits, than be picked or skipped on a number.
Every program ends in a WhatsApp link instead. `HomepageHasNoPricesTest` holds it.
"""

import json

from django.utils.text import capfirst

from . import business
from .seo import SHARE_IMAGE, absolute_static

SEO_TITLE = "Mulai Gym Bandung | Gym Pemula yang Nyaman & Ramah"


def claims(stats):
    """Each live number as a phrase, or "" when there is no number to stand on.

    Written once here and read by the program cards, the FAQ, the search snippet
    and the template, so the wording and the fallback cannot drift apart.
    """
    size = stats.get("pemula_class_size")
    semi = stats.get("semi_private_size")
    alat = stats.get("equipment_total")
    all_videos = bool(alat) and stats.get("equipment_all_have_video")
    return {
        "pemula_size": f"maks {size} orang" if size else "",
        "semi_size": f"maks {semi} orang" if semi else "",
        "equipment": f"{alat} alat" if alat else "",
        "equipment_videos": f"{alat} alat, semua ada video tutorialnya" if all_videos else "",
        "all_videos": all_videos,
    }


def seo_description(stats):
    said = claims(stats)
    kelas = f"Kelas Pemula {said['pemula_size']}" if said["pemula_size"] else "ada Kelas Pemula"
    return (
        f"Gym buat pemula di {business.STREET_SHORT}, {business.CITY}. Coach sabar & tersertifikasi, "
        f"{kelas}, bisa cicilan tanpa kartu kredit. Tanya-tanya gratis."
    )


def whatsapp_links():
    return {
        "general": business.whatsapp_url("Halo Mulai Gym, aku mau tanya-tanya dulu."),
        "visit": business.whatsapp_url("Halo Mulai Gym, aku mau mampir lihat tempatnya."),
        "ramadan": business.whatsapp_url("Halo Mulai Gym, mau tanya tentang program Ramadan"),
    }


def programs(stats):
    said = claims(stats)

    def ask(name):
        return business.whatsapp_url(f"Halo Mulai Gym, aku mau tanya harga {name}.")

    return [
        {
            "key": "gym",
            "icon": "fa-dumbbell",
            "title": "Gym",
            "badge": "",
            "text": "Akses semua alat selama jam buka. Cocok kalau kamu mau latihan sendiri, dibantu Panduan Alat.",
            "points": [
                said["equipment_videos"] or "Cara pakai alat ada di Panduan Alat",
                "Datang kapan aja selama jam buka",
                "Ada pilihan sekali datang",
            ],
            "ask_url": ask("membership gym"),
        },
        {
            "key": "pemula",
            "icon": "fa-people-group",
            "title": "Kelas Pemula",
            "badge": "Paling pas buat pemula",
            "text": f"Latihan bareng {said['pemula_size'] or 'dalam kelompok kecil'}, dipimpin 1 coach.",
            "points": [
                "Push, Pull, dan Leg & Core",
                "Jadwal pagi dan sore",
                "Booking lewat website",
                "Paketnya sudah termasuk akses gym",
            ],
            "ask_url": ask("Kelas Pemula"),
        },
        {
            "key": "semi",
            "icon": "fa-user-group",
            "title": "Semi Private",
            "badge": "",
            "text": (
                f"Kayak latihan sama personal trainer, tapi bareng {said['semi_size'] or 'beberapa orang'}. "
                "Coach-nya muter, bimbing satu-satu."
            ),
            "points": ["Program lebih personal", "Jadwal pagi dan sore", "Paketnya sudah termasuk akses gym"],
            "ask_url": ask("Semi Private"),
        },
        {
            "key": "pt",
            "icon": "fa-user",
            "title": "Personal Trainer",
            "badge": "",
            "text": "1 coach, khusus buat kamu. Buat yang mau program paling personal.",
            "points": ["Latihan 1-on-1", "Program disusun khusus buat kamu"],
            "ask_url": ask("Personal Trainer"),
        },
    ]


def faqs(stats):
    said = claims(stats)
    share = stats.get("pemula_share")
    female = stats.get("female_percent")

    beginners = (
        f"{capfirst(share)} member kami juga mulai dari nol."
        if share
        else "Banyak member kami juga mulai dari nol."
    )
    guides = (
        "semua alat ada video tutorialnya di Panduan Alat"
        if said["all_videos"]
        else "cara pakai alatnya ada di Panduan Alat"
    )
    hours = ", ".join(f"{days} {time}" for days, time in business.opening_hours_rows())

    items = [
        (
            "Aku belum pernah nge-gym sama sekali. Beneran nggak apa-apa?",
            f"Justru Mulai Gym dibikin buat kamu. {beginners} Coach bakal nemenin dari "
            "cara pakai alat yang paling dasar, dan nggak ada pertanyaan yang terlalu dasar.",
        ),
        (
            "Harus ikut kelas?",
            f"Nggak harus. Kamu bisa latihan sendiri, dan {guides}. Kalau mau ditemenin, "
            "ada Kelas Pemula, Semi Private, atau Personal Trainer.",
        ),
        (
            "Bedanya Kelas Pemula, Semi Private, dan Personal Trainer apa?",
            f"Kelas Pemula itu latihan bareng {said['pemula_size'] or 'dalam kelompok kecil'}, "
            "dipimpin 1 coach. Semi Private kayak personal trainer tapi bareng "
            f"{said['semi_size'] or 'beberapa orang'}, coach-nya muter bimbing satu-satu. "
            "Personal Trainer itu 1 coach khusus buat kamu.",
        ),
        (
            "Berapa harganya?",
            "Tergantung program dan durasinya. Chat kami di WhatsApp, tanya-tanya gratis, "
            "nanti admin bantu cariin yang paling pas buat kamu.",
        ),
        (
            "Bisa bayar cicilan?",
            "Bisa. Cicilannya tanpa kartu kredit dan tanpa bunga. Tanya admin buat detailnya.",
        ),
        (
            "Boleh coba sekali datang dulu?",
            "Boleh. Ada pilihan sekali datang, jadi kamu bisa coba dulu sebelum ambil "
            "membership. Kalau cuma mau lihat-lihat tempatnya, mampir aja.",
        ),
        (
            "Kalau aku sakit atau harus ke luar kota lama?",
            "Membership bisa di-freeze, jadi masa aktifnya nggak kebuang. Kabarin admin aja.",
        ),
        ("Jam bukanya kapan?", f"{hours}."),
        (
            "Fasilitasnya apa aja?",
            f"Area gym{' dengan ' + said['equipment'] if said['equipment'] else ''}, area kardio, "
            "kamar mandi dengan shower, loker, lounge, musholla, dan parkir motor & mobil.",
        ),
    ]
    if female:
        items.append(
            (
                "Perempuan nyaman nggak latihan di sini?",
                f"Nyaman. {female}% member kami perempuan, dan coach-nya sudah biasa "
                "ngajarin dari nol.",
            )
        )
    items += [
        (
            "Perlu bawa apa?",
            "Baju dan sepatu olahraga, botol minum, dan handuk kecil. Buat nyimpen barang, "
            "ada loker harian dan bulanan.",
        ),
        (
            "Lokasinya di mana?",
            f"Di {business.STREET}, {business.CITY}, {business.LANDMARK_MID_SENTENCE}. "
            f"Banyak member kami datang dari {business.nearby_areas_text()}.",
        ),
    ]
    return [{"question": q, "answer": a} for q, a in items]


# Fixed static paths the structured data points at. A path missing from the
# manifest is a 500 in production, so a test walks this list.
STRUCTURED_DATA_IMAGES = [SHARE_IMAGE, "images/home/storefront.webp", "images/home/fac-gym.webp"]
LOGO_IMAGE = "favicons/web-app-manifest-512x512.png"


def structured_data(faq_items):
    """schema.org blocks for the homepage: the gym, the site, and the FAQ.

    No aggregateRating on purpose. Google treats a business rating its own site
    reports about itself as self-serving and never shows stars for it, so it
    would be noise at best. The Google Maps listing already carries the real one.
    """
    hours = [
        {
            "@type": "OpeningHoursSpecification",
            "dayOfWeek": business.DAY_NAMES_SCHEMA[day],
            "opens": f"{opens:%H:%M}",
            "closes": f"{closes:%H:%M}",
        }
        for day, (opens, closes) in business.OPENING_TIMES.items()
    ]
    amenities = ["Kamar mandi & shower", "Loker", "Musholla", "Parkir motor & mobil", "Lounge"]
    gym = {
        "@context": "https://schema.org",
        "@type": "ExerciseGym",
        "@id": f"{business.SITE_URL}/#gym",
        "name": business.NAME,
        "alternateName": "Mulai Gym Bandung",
        "description": "Gym yang nyaman dan ramah buat pemula di Bandung, dengan Kelas Pemula, Semi Private, dan Personal Trainer.",
        "url": f"{business.SITE_URL}/",
        "logo": absolute_static(LOGO_IMAGE),
        "image": [url for url in map(absolute_static, STRUCTURED_DATA_IMAGES) if url],
        "telephone": business.PHONE_INTERNATIONAL,
        "address": {
            "@type": "PostalAddress",
            "streetAddress": f"{business.STREET}, {business.KELURAHAN}, {business.KECAMATAN}",
            "addressLocality": business.CITY,
            "postalCode": business.POSTAL_CODE,
            "addressRegion": business.REGION,
            "addressCountry": "ID",
        },
        "geo": {
            "@type": "GeoCoordinates",
            "latitude": business.LATITUDE,
            "longitude": business.LONGITUDE,
        },
        "hasMap": business.MAPS_URL,
        "openingHoursSpecification": hours,
        "amenityFeature": [
            {"@type": "LocationFeatureSpecification", "name": name, "value": True}
            for name in amenities
        ],
        # The three methods payments are actually recorded with.
        "paymentAccepted": "Transfer, QRIS, Tunai",
        "sameAs": [
            business.INSTAGRAM_URL,
            business.TIKTOK_URL,
            business.FACEBOOK_URL,
            business.MAPS_URL,
        ],
    }
    website = {
        "@context": "https://schema.org",
        "@type": "WebSite",
        "name": business.NAME,
        "alternateName": "Mulai Gym Bandung",
        "url": f"{business.SITE_URL}/",
        "inLanguage": "id-ID",
    }
    faq = {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {
                "@type": "Question",
                "name": item["question"],
                "acceptedAnswer": {"@type": "Answer", "text": item["answer"]},
            }
            for item in faq_items
        ],
    }
    return [gym, website, faq]


def as_ld_json(block):
    """JSON for a <script type="application/ld+json">, safe to drop into HTML.

    `<`, `>` and `&` are escaped so no string in the data can close the script tag.
    """
    text = json.dumps(block, ensure_ascii=False)
    return text.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
