from edit import sub
sub('index.js','''		throw new TypeError(`Expected \\`backpressure\\` to be an integer from \\`concurrency\\` (${concurrency}) and up or \\`Infinity\\`, got \\`${backpressure}\\` (${typeof backpressure})`);''','''		throw limitError('backpressure', `\\`concurrency\\` (${concurrency})`, backpressure);''')
sub('index.js','''		throw new TypeError(`Expected \\`concurrency\\` to be an integer from 1 and up or \\`Infinity\\`, got \\`${concurrency}\\` (${typeof concurrency})`);''','''		throw limitError('concurrency', 1, concurrency);''')
sub('index.js','''// Whether the value is an integer from `minimum` and up''','''// The error for a `concurrency` or `backpressure` that is not a valid limit, so both read the same.
function limitError(name, minimum, value) {
	return new TypeError(`Expected \\`${name}\\` to be an integer from ${minimum} and up or \\`Infinity\\`, got \\`${value}\\` (${typeof value})`);
}

// Whether the value is an integer from `minimum` and up''')
