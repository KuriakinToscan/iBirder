import piexif
import sys
import shutil

img_path = sys.argv[1] # Pass a sample JPG
test_img = "test_exif.jpg"
shutil.copy(img_path, test_img)

try:
    exif_dict = piexif.load(test_img)
except Exception:
    exif_dict = {"0th": {}, "Exif": {}, "GPS": {}, "1st": {}, "Interop": {}}

# XP Tags expect utf-16-le bytes. Actually, piexif expects tuple of ints if type is BYTE. Let's test just passing bytes.
# According to EXIF spec, XP tags are BYTE (Type 1). piexif dump converts bytes or tuple.
def to_bytes(s):
    # Some readers require null termination in utf-16le, so \x00\x00
    b = s.encode("utf-16le") + b'\x00\x00'
    return tuple(b) # piexif prefers tuple of ints for BYTE

exif_dict["0th"][piexif.ImageIFD.Software] = b"iBirder"
exif_dict["0th"][18246] = 5 # Rating (Short)
exif_dict["0th"][40091] = to_bytes("Teste Título EXIF")
exif_dict["0th"][40095] = to_bytes("Teste Assunto EXIF")
exif_dict["0th"][40094] = to_bytes("Marca1; Marca2;")

exif_bytes = piexif.dump(exif_dict)
piexif.insert(exif_bytes, test_img)
print("Saved successfuliy to: ", test_img)
