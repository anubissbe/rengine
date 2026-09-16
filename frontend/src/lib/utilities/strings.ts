export const getInitials = (name: string): string => {
	return name
		.split(' ')
		.map((n) => n[0])
		.join('')
		.toUpperCase()
		.slice(0, 2);
};

/** `3 findings`, `1 finding`. The plural defaults to the singular with an s. */
export const plural = (n: number, one: string, many = `${one}s`): string =>
	`${n.toLocaleString()} ${n === 1 ? one : many}`;

/** The noun alone, without the count. */
export const pluralWord = (n: number, one: string, many = `${one}s`): string =>
	n === 1 ? one : many;
