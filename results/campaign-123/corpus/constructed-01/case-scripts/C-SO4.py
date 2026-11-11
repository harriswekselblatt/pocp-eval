from edit import sub
sub('index.js','''	// A null prototype, like `Promise.allKeyed`, so a key like `__proto__` or `toString` is an own property like any other.
	return Object.setPrototypeOf(Object.fromEntries(mappedEntries), null);''','''	// A null prototype, like `Promise.allKeyed`, so a key like `__proto__` or `toString` is an own property like any other. It is built that way from the start, rather than changing the prototype afterwards, which engines handle slowly.
	const output = Object.create(null);

	for (const [key, value] of mappedEntries) {
		output[key] = value;
	}

	return output;''')
