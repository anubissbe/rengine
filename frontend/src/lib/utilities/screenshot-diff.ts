export interface DiffBox {
	x: number;
	y: number;
	w: number;
	h: number;
}

export interface ScreenshotDiff {
	width: number;
	height: number;
	boxes: DiffBox[];
	ratio: number;
}

const BLOCK = 12;
const SAMPLE = 2;
const THRESHOLD = 28;
const MAX_HEIGHT = 6000;

function load(src: string): Promise<HTMLImageElement> {
	return new Promise((resolve, reject) => {
		const img = new Image();
		img.onload = () => resolve(img);
		img.onerror = () => reject(new Error('Screenshot not loaded'));
		img.src = src;
	});
}

function pixels(img: HTMLImageElement, width: number, height: number): Uint8ClampedArray {
	const canvas = document.createElement('canvas');
	canvas.width = width;
	canvas.height = height;
	const ctx = canvas.getContext('2d', { willReadFrequently: true });
	if (!ctx) throw new Error('Canvas not available');
	ctx.drawImage(img, 0, 0, width, height);
	return ctx.getImageData(0, 0, width, height).data;
}

/** Blocks where the two captures differ, in the after image's pixel space. */
export async function screenshotDiff(beforeSrc: string, afterSrc: string): Promise<ScreenshotDiff> {
	const [before, after] = await Promise.all([load(beforeSrc), load(afterSrc)]);
	const width = after.naturalWidth;
	const height = Math.min(after.naturalHeight, MAX_HEIGHT);
	const a = pixels(before, width, height);
	const b = pixels(after, width, height);
	const cols = Math.ceil(width / BLOCK);
	const rows = Math.ceil(height / BLOCK);
	const changed: boolean[] = new Array(cols * rows).fill(false);
	let count = 0;
	for (let by = 0; by < rows; by++) {
		for (let bx = 0; bx < cols; bx++) {
			let sum = 0;
			let n = 0;
			const yEnd = Math.min(height, (by + 1) * BLOCK);
			const xEnd = Math.min(width, (bx + 1) * BLOCK);
			for (let y = by * BLOCK; y < yEnd; y += SAMPLE) {
				for (let x = bx * BLOCK; x < xEnd; x += SAMPLE) {
					const i = (y * width + x) * 4;
					sum +=
						Math.abs(a[i] - b[i]) + Math.abs(a[i + 1] - b[i + 1]) + Math.abs(a[i + 2] - b[i + 2]);
					n++;
				}
			}
			if (n && sum / (n * 3) > THRESHOLD) {
				changed[by * cols + bx] = true;
				count++;
			}
		}
	}
	const boxes: DiffBox[] = [];
	for (let by = 0; by < rows; by++) {
		let start = -1;
		for (let bx = 0; bx <= cols; bx++) {
			const on = bx < cols && changed[by * cols + bx];
			if (on && start < 0) start = bx;
			if (!on && start >= 0) {
				boxes.push({
					x: start * BLOCK,
					y: by * BLOCK,
					w: (bx - start) * BLOCK,
					h: BLOCK
				});
				start = -1;
			}
		}
	}
	return { width, height, boxes, ratio: cols * rows ? count / (cols * rows) : 0 };
}
