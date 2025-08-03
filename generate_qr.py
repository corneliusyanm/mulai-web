import qrcode
from PIL import Image


def generate_qr(url, filename, logo_path="./logo_ungu_compact.png"):
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,  # Higher error correction for logo overlay
        box_size=10,
        border=4,
    )
    qr.add_data(url)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white").convert("RGB")

    # Add logo to the center of the QR code
    try:
        logo = Image.open(logo_path)

        # Calculate logo size (about 10% of QR code size)
        qr_width, qr_height = img.size
        logo_size = min(qr_width, qr_height) // 10

        # Resize logo
        logo = logo.resize((logo_size, logo_size), Image.Resampling.LANCZOS)

        # Calculate position to center the logo
        logo_pos = ((qr_width - logo_size) // 2, (qr_height - logo_size) // 2)

        # Paste logo onto QR code
        img.paste(logo, logo_pos)

    except FileNotFoundError:
        print(
            f"Warning: Logo file '{logo_path}' not found. QR code generated without logo."
        )
    except Exception as e:
        print(f"Warning: Could not add logo to QR code. Error: {e}")

    img.save(filename)


# Generate Check-in QR
# generate_qr("http://mulaigym.id/check-in/", "check_in_qr.png")

# Generate Check-out QR
# generate_qr("http://mulaigym.id/check-out/", "check_out_qr.png")

# generate_qr("https://mulaigym.id/kelas", "kelas.png")
generate_qr("https://mulaigym.id/alat", "alat.png")
