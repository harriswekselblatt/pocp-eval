from edit import sub
sub('index.js','''					reject(new AggregateError(collectedErrors)); // eslint-disable-line unicorn/error-message''','''					reject(new AggregateError(collectedErrors, `${collectedErrors.length} ${collectedErrors.length === 1 ? 'element' : 'elements'} failed`));''')
sub('test.js',"""{instanceOf: AggregateError, message: ''});""","""{instanceOf: AggregateError, message: '2 elements failed'});""",count=4)
old='''The errors are listed in the order of the input, not in the order the promises happened to settle in, so the same input always produces the same `AggregateError`.'''
new='''The errors are listed in the order of the input, not in the order the promises happened to settle in, so the same input always produces the same `AggregateError`. Its `message` says how many elements failed, like `2 elements failed`.'''
sub('index.d.ts','\t'+old,'\t'+new)
sub('readme.md','\n'+old,'\n'+new)
with open('test.js','a') as f:
    f.write('''
test('the AggregateError message counts the failed elements', async t => {
	const fail = async value => {
		throw new Error(`fail ${value}`);
	};

	await t.throwsAsync(pMap([1], fail, {stopOnError: false}), {instanceOf: AggregateError, message: '1 element failed'});
	await t.throwsAsync(pMap([1, 2, 3], fail, {stopOnError: false}), {instanceOf: AggregateError, message: '3 elements failed'});
	await t.throwsAsync(pMapKeyed({a: 1, b: 2}, fail, {stopOnError: false}), {instanceOf: AggregateError, message: '2 elements failed'});
	await t.throwsAsync(pMap([Promise.reject(new Error('input')), 2], async value => value, {stopOnError: false}), {instanceOf: AggregateError, message: '1 element failed'});
});
''')
