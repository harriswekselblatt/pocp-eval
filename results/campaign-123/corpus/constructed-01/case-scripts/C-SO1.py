from edit import sub
sub('index.js','''		const iterator = getIterator(iterable);

		const signalListener''','''		const iterator = getIterator(iterable);

		// Close the source so it can release its resources, like `for await` does, unless it already reported `done`.
		const closeSourceUnlessDone = () => {
			if (!isIterableDone) {
				closeIterator(iterator);
			}
		};

		const signalListener''')
sub('index.js','''			reject_(reason);
			cleanup();

			if (!isIterableDone) {
				closeIterator(iterator);
			}
		};''','''			reject_(reason);
			cleanup();
			closeSourceUnlessDone();
		};''')
sub('index.js','''			// A stop ended the result before the source did, so close it, like `for await` does on a `break`. Not at the stop itself, as a source that settles its `next()` calls out of call order may still owe an earlier element, and closing could drop it.
			if (!isIterableDone) {
				closeIterator(iterator);
			}
''','''			// A stop ended the result before the source did, so close it, like `for await` does on a `break`. Not at the stop itself, as a source that settles its `next()` calls out of call order may still owe an earlier element, and closing could drop it.
			closeSourceUnlessDone();
''')
