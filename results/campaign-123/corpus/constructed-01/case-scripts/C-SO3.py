from edit import sub
sub('index.js','''				const collectedErrors = [];

				for (let index = 0; index < Math.min(doneIndex, errors.length); index++) {
					if (index in errors) {
						collectedErrors.push(errors[index]);
					}
				}
''','''				// `slice` keeps the holes left by the indexes that did not fail, and `filter` skips holes, so the errors stay in input order, including an error that is `undefined`.
				const collectedErrors = errors.slice(0, doneIndex).filter(() => true);
''')
