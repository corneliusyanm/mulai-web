import qrcode


def generate_qr(url, filename):
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(url)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    img.save(filename)


# Generate Check-in QR
generate_qr("http://mulaigym.id/check-in/", "check_in_qr.png")

# Generate Check-out QR
generate_qr("http://mulaigym.id/check-out/", "check_out_qr.png")

print("QR codes generated successfully!")
print("- check_in_qr.png")
print("- check_out_qr.png")
