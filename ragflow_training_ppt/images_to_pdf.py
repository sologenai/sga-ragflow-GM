import os
import img2pdf

BASE_PATH = r"e:\sga-ragflow-GM\ragflow_training_ppt"
IMAGE_PATH = os.path.join(BASE_PATH, "images")
PDF_FILE = os.path.join(BASE_PATH, "RAGFlow_Training_XiamenITG_v2.pdf")

# Get all slide images sorted by name
image_files = []
for i in range(1, 29):
    img_file = os.path.join(IMAGE_PATH, f"slide_{i:02d}.png")
    if os.path.exists(img_file):
        image_files.append(img_file)
        print(f"  Adding: slide_{i:02d}.png")
    else:
        print(f"  Missing: slide_{i:02d}.png")

if image_files:
    with open(PDF_FILE, "wb") as f:
        f.write(img2pdf.convert(image_files))
    print(f"\n✅ PDF saved to: {PDF_FILE}")
else:
    print("No images found!")
