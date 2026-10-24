import sys
from pathlib import Path

from PIL import Image

FRAME_MS = 110
COLORS = 255


def main(frames_dir: Path, target: Path, width: int) -> None:
    frames = []
    for path in sorted(frames_dir.glob("f*.png")):
        image = Image.open(path).convert("RGB")
        frames.append(image.resize((width, round(image.height * width / image.width)), Image.LANCZOS))
    palette = frames[len(frames) // 2].quantize(colors=COLORS, method=Image.MEDIANCUT)
    quantized = [frame.quantize(palette=palette, dither=Image.Dither.NONE) for frame in frames]
    quantized[0].save(
        target, save_all=True, append_images=quantized[1:], duration=FRAME_MS, loop=0, optimize=True, disposal=1
    )
    print(f"{len(frames)} frames, {target.stat().st_size // 1024} KB")


if __name__ == "__main__":
    main(Path(sys.argv[1]), Path(sys.argv[2]), int(sys.argv[3]))
