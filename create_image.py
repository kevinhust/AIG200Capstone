from PIL import Image, ImageDraw

def create_dummy_image(path="test_meal.jpg"):
    img = Image.new('RGB', (224, 224), color = (73, 109, 137))
    d = ImageDraw.Draw(img)
    d.text((10,10), "Food", fill=(255, 255, 0))
    img.save(path)
    print(f"Created {path}")

if __name__ == "__main__":
    create_dummy_image()
