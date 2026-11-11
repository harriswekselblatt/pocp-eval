from edit import sub
sub('index.js','''// Pull the next item, and stop pulling once''','''// What a pull answers once the source is done. One shared object, as callers only read it.
const doneItem = Object.freeze({done: true});

// Pull the next item, and stop pulling once''')
sub('index.js','''		if (isSourceDone) {
			return {done: true};
		}''','''		if (isSourceDone) {
			return doneItem;
		}''')
