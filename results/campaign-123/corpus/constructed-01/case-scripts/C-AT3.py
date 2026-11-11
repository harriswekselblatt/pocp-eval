with open('test.js','a') as f:
    f.write('''
test('pMapSettled - maps a string by code point', async t => {
	const result = await pMapSettled('a\\u{1F600}b', value => value.toUpperCase());

	t.deepEqual(result, [
		{status: 'fulfilled', value: 'A'},
		{status: 'fulfilled', value: '\\u{1F600}'},
		{status: 'fulfilled', value: 'B'},
	]);
});
''')
