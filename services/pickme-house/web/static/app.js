(function () {
	const actionSelect = document.getElementById('action-select');
	const levelSelect = document.getElementById('level-select');

	const groups = {
		plain: document.getElementById('plain-group'),
		ct: document.getElementById('ct-group'),
		key: document.getElementById('key-group'),
		nonce: document.getElementById('nonce-group'),
		n: document.getElementById('n-group'),
		d: document.getElementById('d-group'),
		keylit: document.getElementById('keyliteral-group')
	};

	function setHidden(el, hide) {
		if (!el) return;
		const inputs = el.querySelectorAll('input, textarea, select');
		if (hide) {
			el.classList.add('hidden');
			el.classList.remove('fade-in');
			el.setAttribute('aria-hidden', 'true');
			inputs.forEach(i => i.setAttribute('disabled', 'disabled'));
		} else {
			el.classList.remove('hidden');
			void el.offsetWidth;
			el.classList.add('fade-in');
			el.removeAttribute('aria-hidden');
			inputs.forEach(i => i.removeAttribute('disabled'));
		}
	}

	function focusFirstVisible() {
		for (const k of ['plain','ct','key','nonce','n','d','keylit']) {
			const el = groups[k];
			if (el && !el.classList.contains('hidden')) {
				const first = el.querySelector('input, textarea, select, button');
				if (first) { first.focus(); break; }
			}
		}
	}

	function updateUI() {
		if (!actionSelect || !levelSelect) return;
		const action = actionSelect.value;
		const level = parseInt(levelSelect.value, 10);

		Object.values(groups).forEach(g => setHidden(g, true));

			if (action === 'encrypt') {
				setHidden(groups.plain, false);
			} else {
				if (level === 1) {
					setHidden(groups.ct, false);
					setHidden(groups.keylit, false);
				} else if (level === 2) {
					setHidden(groups.ct, false);
					setHidden(groups.key, false);
					setHidden(groups.nonce, false);
				} else if (level === 3) {
					setHidden(groups.ct, false);
					setHidden(groups.n, false);
					setHidden(groups.d, false);
				} else {
					setHidden(groups.ct, false);
				}
			}

		focusFirstVisible();
	}

	if (actionSelect && levelSelect) {
		actionSelect.addEventListener('change', updateUI);
		levelSelect.addEventListener('change', updateUI);
		window.addEventListener('load', updateUI);
	}

	const resultPanel = document.getElementById('result-panel');
	if (resultPanel) {
		resultPanel.classList.add('glow');
		setTimeout(() => resultPanel.classList.remove('glow'), 1800);
	}
})();

(function() {
	if (document.body.classList.contains('girly-page')) return;

	function createTextGlitch(element) {
		if (!element) return;
		
		const originalText = element.textContent;
		const glitchChars = ['█', '▓', '▒', '░', '▄', '▀', '■', '□'];
		
		setInterval(() => {
			if (Math.random() < 0.1) {
				const chars = originalText.split('');
				const glitchCount = Math.floor(Math.random() * 3) + 1;
				
				for (let i = 0; i < glitchCount; i++) {
					const pos = Math.floor(Math.random() * chars.length);
					if (chars[pos] !== ' ') {
						chars[pos] = glitchChars[Math.floor(Math.random() * glitchChars.length)];
					}
				}
				
				element.textContent = chars.join('');
				
				setTimeout(() => {
					element.textContent = originalText;
				}, 50 + Math.random() * 100);
			}
		}, 2000 + Math.random() * 3000);
	}

	const title = document.querySelector('.title');
	if (title) createTextGlitch(title);

	function randomDistort() {
		const cards = document.querySelectorAll('.card');
		cards.forEach(card => {
			if (Math.random() < 0.05) {
				card.style.transform = `perspective(1000px) rotateX(${(Math.random() - 0.5) * 2}deg) rotateY(${(Math.random() - 0.5) * 2}deg)`;
				setTimeout(() => {
					card.style.transform = '';
				}, 200);
			}
		});
	}

	setInterval(randomDistort, 3000);

	const buttons = document.querySelectorAll('.btn');
	buttons.forEach(btn => {
		btn.addEventListener('mouseenter', function() {
			if (Math.random() < 0.3) {
				this.style.animation = 'none';
				setTimeout(() => {
					this.style.animation = '';
				}, 10);
			}
		});
	});

	const inputs = document.querySelectorAll('input, textarea, select');
	inputs.forEach(input => {
		input.addEventListener('focus', function() {
			if (Math.random() < 0.2) {
				this.style.boxShadow = '0 0 30px rgba(255, 0, 0, 0.8), inset 0 0 25px rgba(0, 0, 0, 0.9)';
				setTimeout(() => {
					this.style.boxShadow = '';
				}, 300);
			}
		});
	});

	window.addEventListener('load', function() {
		setTimeout(() => {
			if (Math.random() < 0.3) {
				document.body.style.filter = 'brightness(0.8) contrast(1.2)';
				setTimeout(() => {
					document.body.style.filter = '';
				}, 200);
			}
		}, 1000);
	});

	function panelGlitch() {
		const panels = document.querySelectorAll('.panel');
		panels.forEach(panel => {
			if (Math.random() < 0.08) {
				panel.style.opacity = '0.7';
				panel.style.transform = 'translateX(' + (Math.random() - 0.5) * 4 + 'px)';
				setTimeout(() => {
					panel.style.opacity = '';
					panel.style.transform = '';
				}, 100);
			}
		});
	}

	setInterval(panelGlitch, 4000);

	const resultBox = document.querySelector('.result-box');
	if (resultBox) {
		const observer = new MutationObserver(function(mutations) {
			mutations.forEach(() => {
				if (Math.random() < 0.15) {
					resultBox.style.textShadow = '0 0 10px rgba(255, 0, 0, 0.8)';
					setTimeout(() => {
						resultBox.style.textShadow = '';
					}, 500);
				}
			});
		});
		
		observer.observe(resultBox, { childList: true, subtree: true });
	}

	document.addEventListener('mousemove', function(e) {
		if (Math.random() < 0.01) {
			document.body.style.transform = `translate(${(Math.random() - 0.5) * 2}px, ${(Math.random() - 0.5) * 2}px)`;
			setTimeout(() => {
				document.body.style.transform = '';
			}, 50);
		}
	});

	const notice = document.querySelector('.notice');
	if (notice) {
		setInterval(() => {
			if (Math.random() < 0.2) {
				notice.style.borderLeftWidth = '6px';
				notice.style.boxShadow = '0 0 30px rgba(255, 0, 0, 0.6)';
				setTimeout(() => {
					notice.style.borderLeftWidth = '';
					notice.style.boxShadow = '';
				}, 300);
			}
		}, 5000);
	}
})();