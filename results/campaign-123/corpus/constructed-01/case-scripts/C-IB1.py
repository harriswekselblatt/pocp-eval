from edit import sub
sub('index.js','''or \\`AsyncIterable\\`, got (${typeof iterable})`);''','''or \\`AsyncIterable\\`, got (${iterable === null ? 'null' : typeof iterable})`);''')
sub('index.js','''	// Optional chaining, so a nullish input gets this message rather than Node's internal
	// "null is not iterable".''','''	// Optional chaining, so a nullish input gets this message rather than Node's internal
	// "null is not iterable". `null` is named as such, like the keyed functions do, rather than as `object`.''')
sub('test.js',"""await t.throwsAsync(pMap(null, async () => {}), {message: 'Expected `input` to be either an `Iterable` or `AsyncIterable`, got (object)'});""","""await t.throwsAsync(pMap(null, async () => {}), {message: 'Expected `input` to be either an `Iterable` or `AsyncIterable`, got (null)'});""")
sub('test.js',"""t.throws(() => pMapIterable(null, async () => {}), {message: 'Expected `input` to be either an `Iterable` or `AsyncIterable`, got (object)'});""","""t.throws(() => pMapIterable(null, async () => {}), {message: 'Expected `input` to be either an `Iterable` or `AsyncIterable`, got (null)'});""")
