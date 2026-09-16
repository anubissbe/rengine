import { describe, expect, it } from 'vitest';
import { getInitials, plural, pluralWord } from './strings';

describe('plural', () => {
	it('agrees with the count', () => {
		expect(plural(1, 'finding')).toBe('1 finding');
		expect(plural(0, 'finding')).toBe('0 findings');
		expect(plural(2, 'finding')).toBe('2 findings');
	});

	it('takes an irregular plural', () => {
		expect(plural(2, 'excluded IP', 'excluded IPs')).toBe('2 excluded IPs');
	});

	it('groups thousands', () => {
		expect(plural(12000, 'web asset')).toBe('12,000 web assets');
	});
});

describe('pluralWord', () => {
	it('carries the noun without the count', () => {
		expect(pluralWord(1, 'scan')).toBe('scan');
		expect(pluralWord(3, 'scan')).toBe('scans');
	});
});

describe('getInitials', () => {
	it('takes two letters at most', () => {
		expect(getInitials('ada lovelace')).toBe('AL');
		expect(getInitials('grace brewster murray hopper')).toBe('GB');
	});
});
