import qrcode
from PIL import Image, ImageDraw, ImageFont
import os


def generate_styled_qr(
    url,
    filename,
    equipment_name=None,
    logo_path="../static/images/logo_white.png",
    output_dir="generated_qr",
):
    """
    Generate a styled QR code with Mulai Gym branding

    Args:
        url: The URL to encode
        filename: Output filename (without path)
        equipment_name: Name of the equipment for the label
        logo_path: Path to the logo file
        output_dir: Output directory for generated files
    """

    # Mulai Gym brand colors
    PRIMARY_COLOR = "#4B4BEC"  # Blue/purple
    SECONDARY_COLOR = "#BEF006"  # Lime green
    BACKGROUND_COLOR = "#FFFFFF"  # White
    TEXT_COLOR = "#343434"  # Dark gray

    # Convert hex colors to RGB tuples
    def hex_to_rgb(hex_color):
        return tuple(int(hex_color[i : i + 2], 16) for i in (1, 3, 5))

    primary_rgb = hex_to_rgb(PRIMARY_COLOR)
    secondary_rgb = hex_to_rgb(SECONDARY_COLOR)
    text_rgb = hex_to_rgb(TEXT_COLOR)

    # Create QR code with better scanning parameters
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,  # Optimized for logo overlay
        border=3,  # Standard border for better scanning
    )
    qr.add_data(url)
    qr.make(fit=True)

    # Generate QR code with Mulai Gym purple color
    qr_img = qr.make_image(fill_color=primary_rgb, back_color=BACKGROUND_COLOR).convert(
        "RGB"
    )

    # Create an ultra compact canvas for branding elements
    qr_width, qr_height = qr_img.size
    canvas_width = qr_width + 20  # Ultra small padding
    canvas_height = qr_height + 60  # Ultra small spacing for text

    # Create main canvas
    canvas = Image.new("RGB", (canvas_width, canvas_height), BACKGROUND_COLOR)

    # Calculate positions for ultra compact layout
    qr_x = (canvas_width - qr_width) // 2
    qr_y = 28  # Ultra small space for title

    # Paste QR code on canvas
    canvas.paste(qr_img, (qr_x, qr_y))

    # Add text elements
    draw = ImageDraw.Draw(canvas)

    # Better font handling with multiple fallbacks
    def get_font(size, bold=False):
        font_names = [
            "Arial-Bold" if bold else "Arial",
            "Helvetica-Bold" if bold else "Helvetica",
            "DejaVu Sans Bold" if bold else "DejaVu Sans",
            "/System/Library/Fonts/Helvetica.ttc",
            "/System/Library/Fonts/Arial.ttf",
        ]

        for font_name in font_names:
            try:
                return ImageFont.truetype(font_name, size)
            except (OSError, IOError):
                continue

        # Final fallback - scaled default font
        try:
            font = ImageFont.load_default()
            # Try to get a better default font if available
            return ImageFont.load_default()
        except:
            return ImageFont.load_default()

    title_font = get_font(24, bold=True)
    subtitle_font = get_font(16)
    url_font = get_font(16)

    # Add title with very compact positioning
    title = equipment_name if equipment_name else "MULAI GYM"
    title_bbox = draw.textbbox((0, 0), title, font=title_font)
    title_width = title_bbox[2] - title_bbox[0]
    title_x = (canvas_width - title_width) // 2
    draw.text(
        (title_x, 12), title, fill=text_rgb, font=title_font
    )  # Ultra close to top

    # Add subtitle with very tight spacing
    subtitle = "Scan untuk cara penggunaan & info detail"
    subtitle_bbox = draw.textbbox((0, 0), subtitle, font=subtitle_font)
    subtitle_width = subtitle_bbox[2] - subtitle_bbox[0]
    subtitle_x = (canvas_width - subtitle_width) // 2
    draw.text(
        (subtitle_x, 35), subtitle, fill=(100, 100, 100), font=subtitle_font
    )  # Ultra close to title

    # Add URL at bottom with very compact styling
    url_display = url.replace("https://", "").replace(
        "http://", ""
    )  # Cleaner URL display
    url_bbox = draw.textbbox((0, 0), url_display, font=url_font)
    url_width = url_bbox[2] - url_bbox[0]
    url_x = (canvas_width - url_width) // 2
    draw.text(
        (url_x, canvas_height - 40),
        url_display,
        fill=(120, 120, 120),
        font=url_font,  # Bigger URL font, close to bottom
    )

    # Add bold Mulai Gym accent elements
    accent_height = 10  # Thicker neon borders

    # Top bold neon accent bar
    draw.rectangle([0, 0, canvas_width, accent_height], fill=secondary_rgb)

    # Bottom bold neon accent bar
    draw.rectangle(
        [0, canvas_height - accent_height, canvas_width, canvas_height],
        fill=secondary_rgb,
    )

    # Left bold neon accent bar
    draw.rectangle(
        [0, 0, accent_height, canvas_height],
        fill=secondary_rgb,
    )

    # Right bold neon accent bar
    draw.rectangle(
        [canvas_width - accent_height, 0, canvas_width, canvas_height],
        fill=secondary_rgb,
    )

    # Larger corner accents in purple
    corner_size = 10  # Bigger corner rectangles
    # Top corners
    draw.rectangle([0, 0, corner_size, corner_size], fill=primary_rgb)
    draw.rectangle(
        [canvas_width - corner_size, 0, canvas_width, corner_size], fill=primary_rgb
    )
    # Bottom corners
    draw.rectangle(
        [0, canvas_height - corner_size, corner_size, canvas_height], fill=primary_rgb
    )
    draw.rectangle(
        [
            canvas_width - corner_size,
            canvas_height - corner_size,
            canvas_width,
            canvas_height,
        ],
        fill=primary_rgb,
    )

    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)

    # Save the final image
    output_path = os.path.join(output_dir, filename)
    canvas.save(output_path, quality=95)
    print(f"✅ Generated QR code: {output_path}")

    return output_path


def generate_all_equipment_qrs(urls_file="equipments_url"):
    """
    Generate QR codes for all equipment URLs in the file
    """
    try:
        with open(urls_file, "r") as f:
            urls = [line.strip() for line in f if line.strip()]

        print(f"📋 Found {len(urls)} URLs to process")

        for i, url in enumerate(urls, 1):
            # Extract equipment name from URL
            equipment_name = url.split("/")[-1].replace("-", " ").title()

            # Create filename
            filename = f"{equipment_name.lower().replace(' ', '_')}_qr.png"

            print(f"🔄 Processing {i}/{len(urls)}: {equipment_name}")

            # Generate QR code
            generate_styled_qr(
                url=url, filename=filename, equipment_name=equipment_name
            )

        print(f"🎉 Successfully generated {len(urls)} QR codes!")

    except FileNotFoundError:
        print(f"❌ Error: Could not find URLs file '{urls_file}'")
    except Exception as e:
        print(f"❌ Error generating QR codes: {e}")


# Example usage for single QR
if __name__ == "__main__":
    import sys

    if len(sys.argv) == 1:
        # Generate all equipment QRs
        print("🔄 Generating all equipment QR codes...")
        generate_all_equipment_qrs()
    elif len(sys.argv) >= 3:
        # Generate custom QR: python generate_qr.py "URL" "Title" [filename]
        url = sys.argv[1]
        title = sys.argv[2]
        filename = (
            sys.argv[3]
            if len(sys.argv) > 3
            else f"{title.lower().replace(' ', '_')}_qr.png"
        )

        print(f"🔄 Generating custom QR: {title}")
        generate_styled_qr(url, filename, title)
    else:
        print("Usage:")
        print("  python generate_qr.py                    # Generate all equipment QRs")
        print("  python generate_qr.py 'URL' 'Title'      # Generate custom QR")
        print(
            "  python generate_qr.py 'URL' 'Title' 'filename.png'  # Generate with custom filename"
        )
        print()
