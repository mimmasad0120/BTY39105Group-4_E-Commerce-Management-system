function showLogin(type, clickedButton) {
            document.getElementById('registration').classList.remove('active');
            document.querySelectorAll('.login-form').forEach(form => {
                form.classList.remove('active');
            });

            document.querySelectorAll('.tab').forEach(tab => {
                tab.classList.remove('active');
            });

            document.getElementById(type).classList.add('active');
            clickedButton.classList.add('active');
        }

        function showRegistration(event) {
            event.preventDefault();
            document.getElementById('forgotPassword').classList.remove('active');
            document.querySelectorAll('.login-form').forEach(form => {
                form.classList.remove('active');
            });
            document.querySelectorAll('.tab').forEach(tab => {
                tab.classList.remove('active');
            });
            document.getElementById('registrationFormView').style.display = '';
            document.getElementById('registration').classList.add('active');
        }

        function showForgotPassword(event) {
            event.preventDefault();
            document.getElementById('registration').classList.remove('active');
            document.querySelectorAll('.login-form').forEach(form => {
                form.classList.remove('active');
            });
            document.querySelectorAll('.tab').forEach(tab => {
                tab.classList.remove('active');
            });
            document.getElementById('forgotPassword').classList.add('active');
        }

        function showLoginPage(event) {
            event.preventDefault();
            sessionStorage.removeItem('pendingRegistrationEmail');
            const formView = document.getElementById('registrationFormView');
            const verificationStep = document.getElementById('verificationStep');
            formView.classList.remove('is-exit');
            formView.classList.add('active');
            formView.style.display = '';
            verificationStep.classList.remove('active', 'is-exit');
            document.querySelector('.registration-animation-shell').style.minHeight = '';
            document.getElementById('registration').classList.remove('active');
            document.getElementById('forgotPassword').classList.remove('active');
            document.getElementById('customer').classList.add('active');
            document.querySelector('.tab').classList.add('active');
        }

        function animateRegistrationTransition(showVerification) {
            const formView = document.getElementById('registrationFormView');
            const verificationStep = document.getElementById('verificationStep');
            const animationShell = document.querySelector('.registration-animation-shell');

            if (showVerification) {
                const reservedHeight = Math.max(
                    formView.getBoundingClientRect().height,
                    verificationStep.getBoundingClientRect().height
                );
                animationShell.style.minHeight = `${reservedHeight}px`;
                formView.classList.add('is-exit');
                verificationStep.classList.add('active');
                setTimeout(() => {
                    formView.classList.remove('active');
                    formView.classList.remove('is-exit');
                }, 500);
                return;
            }

            verificationStep.classList.remove('active');
            verificationStep.classList.add('is-exit');
            formView.classList.add('active');
            setTimeout(() => {
                verificationStep.classList.remove('is-exit');
                animationShell.style.minHeight = '';
            }, 460);
        }

        function togglePassword(inputId, button) {
            const input = document.getElementById(inputId);
            const showingPassword = input.type === 'text';
            input.type = showingPassword ? 'password' : 'text';
            button.setAttribute('aria-label', showingPassword ? 'Show password' : 'Hide password');
            button.title = showingPassword ? 'Show password' : 'Hide password';
        }

        function showInfoModal(type) {
            const title = document.getElementById('infoModalTitle');
            const text = document.getElementById('infoModalText');
            if (type === 'terms') {
                title.textContent = 'Terms and Conditions';
                text.textContent = 'Use this marketplace responsibly. Product availability, prices, delivery times, and payment options may change. By placing an order, you agree to provide accurate delivery information and follow the selected payment terms.';
            } else {
                title.textContent = 'Privacy Policy';
                text.textContent = 'We use account, delivery, and order information only to provide marketplace services, process orders, arrange delivery, and support your account. Contact us if you need to update or remove your information.';
            }
            document.getElementById('infoModal').style.display = 'flex';
        }

        function closeInfoModal() {
            document.getElementById('infoModal').style.display = 'none';
        }

        const localHostNames = ['localhost', '127.0.0.1', '[::1]', '::1'];
        const localBackendHost = window.location.hostname.includes(':')
            && !window.location.hostname.startsWith('[')
            ? `[${window.location.hostname}]`
            : window.location.hostname;
        const API_BASE_URL = window.location.protocol === 'file:'
            ? 'http://127.0.0.1:5000'
            : localHostNames.includes(window.location.hostname)
                ? `http://${localBackendHost}:5000`
                : window.location.origin;
        let currentCustomerEmail = '';
        let currentCustomerName = '';
        let currentCustomerAuthToken = '';
        let pendingUpiPaymentOrderIds = [];
        let deliveryAuthToken = '';
        let pendingDeliveryOtpOrderId = null;
        let pendingDeliveryStatusSelect = null;
        let pendingDeliveryStatusPreviousValue = '';
        let customerProducts = [];
        let customerCart = [];
        let customerWishlist = new Set();
        let customerWishlistStorageKey = '';
        let pendingCartProduct = null;
        let appliedCoupon = null;
        let activeProductCategory = 'all';
        let activeProductSearch = '';
        let activeRatingProductId = null;
        let promoSlideIndex = 0;
        let promoTimer;
        const foodImageFallbacks = {
            'French Fries': 'https://images.unsplash.com/photo-1573080496219-bb080dd4f877?auto=format&fit=crop&w=600&q=80',
            'Chicken Burger': 'https://images.unsplash.com/photo-1568901346375-23c9450c58cd?auto=format&fit=crop&w=600&q=80',
            'Margherita Pizza': 'https://images.unsplash.com/photo-1574071318508-1cdbab80d002?auto=format&fit=crop&w=600&q=80',
            'Chicken Biryani': 'https://images.unsplash.com/photo-1563379091339-03b21ab4a4f8?auto=format&fit=crop&w=600&q=80',
            'Chocolate Cake': 'https://images.unsplash.com/photo-1578985545062-69928b1d9587?auto=format&fit=crop&w=600&q=80'
        };

        function getProductImage(product) {
            return product.imageUrl || foodImageFallbacks[product.name] || '';
        }

        function showPromoSlide(index) {
            const slides = document.querySelectorAll('.promo-slide');
            const dots = document.querySelectorAll('.promo-dot');
            if (!slides.length) return;

            promoSlideIndex = (index + slides.length) % slides.length;
            slides.forEach((slide, slideIndex) => slide.classList.toggle('active', slideIndex === promoSlideIndex));
            dots.forEach((dot, dotIndex) => {
                const selected = dotIndex === promoSlideIndex;
                dot.classList.toggle('active', selected);
                dot.setAttribute('aria-selected', selected ? 'true' : 'false');
            });
        }

        function startPromoSlider() {
            clearInterval(promoTimer);
        }

        document.querySelectorAll('.promo-dot').forEach((dot, index) => {
            dot.addEventListener('click', () => {
                showPromoSlide(index);
                startPromoSlider();
            });
        });
        startPromoSlider();

        document.addEventListener('visibilitychange', () => {
            if (document.hidden) clearInterval(promoTimer);
            else startPromoSlider();
        });

        let voiceSearchRecognition;

        function startVoiceSearch() {
            const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
            const searchInput = document.getElementById('productSearch');
            const voiceButton = document.getElementById('voiceSearchButton');

            if (!SpeechRecognition) {
                alert('Voice typing is not supported in this browser. Please use Chrome or Edge.');
                return;
            }

            if (voiceSearchRecognition) {
                voiceSearchRecognition.stop();
                return;
            }

            voiceSearchRecognition = new SpeechRecognition();
            voiceSearchRecognition.lang = 'en-US';
            voiceSearchRecognition.interimResults = false;
            voiceSearchRecognition.maxAlternatives = 1;
            voiceButton.classList.add('listening');
            voiceButton.setAttribute('aria-label', 'Stop voice search');
            voiceButton.title = 'Listening...';

            voiceSearchRecognition.onresult = event => {
                searchInput.value = event.results[0][0].transcript;
                submitProductSearch();
            };

            voiceSearchRecognition.onerror = event => {
                if (event.error !== 'aborted' && event.error !== 'no-speech') {
                    alert('Voice search could not start. Please check your microphone permission.');
                }
            };

            voiceSearchRecognition.onend = () => {
                voiceSearchRecognition = null;
                voiceButton.classList.remove('listening');
                voiceButton.setAttribute('aria-label', 'Start voice search');
                voiceButton.title = 'Search by voice';
            };

            voiceSearchRecognition.start();
        }

        async function readApiResponse(response) {
            const contentType = response.headers.get('content-type') || '';
            if (!contentType.includes('application/json')) {
                throw new Error(`Server returned ${response.status} instead of JSON. Check that the backend is running at ${API_BASE_URL}.`);
            }
            return response.json();
        }

        let registrationOtpSending = false;

        async function registerCustomer(event) {
            event.preventDefault();
            event.stopPropagation();

            if (registrationOtpSending) return;

            const password = document.getElementById('registrationPassword').value;
            const confirmPassword = document.getElementById('confirmPassword').value;

            if (password !== confirmPassword) {
                showErrorToast('Passwords do not match.');
                return;
            }

            const registrationData = {
                fullName: document.getElementById('fullName').value,
                phone: document.getElementById('phone').value,
                email: document.getElementById('registrationEmail').value,
                password,
                confirmPassword
            };

            const verificationStep = document.getElementById('verificationStep');
            const wasVerificationActive = verificationStep.classList.contains('active');
            const submitButton = document.getElementById('registrationSubmitButton');
            const verifyButton = document.getElementById('verifyOtpButton');
            const resendButton = document.getElementById('resendOtpButton');
            const deliveryStatus = document.getElementById('otpDeliveryStatus');

            registrationOtpSending = true;
            submitButton.disabled = true;
            verifyButton.disabled = true;
            resendButton.disabled = true;
            deliveryStatus.textContent = 'Sending your verification code...';
            deliveryStatus.hidden = false;
            document.getElementById('verificationEmail').textContent = registrationData.email.trim();
            if (!wasVerificationActive) animateRegistrationTransition(true);

            try {
                const response = await fetch(`${API_BASE_URL}/api/register`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(registrationData)
                });
                const result = await readApiResponse(response);

                if (!response.ok) {
                    deliveryStatus.hidden = true;
                    if (!wasVerificationActive) animateRegistrationTransition(false);
                    showErrorToast(result.error || 'Email already registered.');
                    return;
                }

                sessionStorage.setItem('pendingRegistrationEmail', result.email);
                document.getElementById('verificationEmail').textContent = result.email;
                deliveryStatus.textContent = 'Code sent. Enter the 6-digit code.';
                showSuccessToast('OTP sent successfully.');
            } catch (error) {
                deliveryStatus.hidden = true;
                if (!wasVerificationActive) animateRegistrationTransition(false);
                showErrorToast(error.message || 'Could not connect to the backend.');
            } finally {
                registrationOtpSending = false;
                submitButton.disabled = false;
                verifyButton.disabled = false;
                resendButton.disabled = false;
            }
        }

        let emailOtpVerifying = false;

        async function verifyEmailOtp(event) {
            event?.preventDefault();
            event?.stopPropagation();
            if (emailOtpVerifying) return;

            const enteredOtp = document.getElementById('verificationCode').value.trim();
            const email = document.getElementById('registrationEmail').value;

            if (!/^\d{6}$/.test(enteredOtp)) {
                showErrorToast('Please enter the 6-digit OTP sent to your email.');
                return;
            }

            const verifyButton = document.getElementById('verifyOtpButton');
            emailOtpVerifying = true;
            verifyButton.disabled = true;

            try {
                const response = await fetch(`${API_BASE_URL}/api/verify-otp`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ email, otp: enteredOtp })
                });
                const result = await readApiResponse(response);

                if (!response.ok) {
                    showErrorToast(result.error || 'Invalid or expired OTP.');
                    return;
                }

                showSuccessToast('Account created successfully. Please log in.');
                document.querySelector('#registrationFormView form').reset();
                document.getElementById('verificationCode').value = '';
                showLoginPage({ preventDefault: () => {} });
            } catch (error) {
                showErrorToast(error.message || 'Could not connect to the backend.');
            } finally {
                emailOtpVerifying = false;
                verifyButton.disabled = false;
            }
        }

        async function resendRegistrationOtp() {
            await registerCustomer({ preventDefault: () => {} });
        }

        async function requestPasswordReset(event) {
            event.preventDefault();
            const email = document.getElementById('resetEmail').value.trim();

            try {
                const response = await fetch(`${API_BASE_URL}/api/forgot-password`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ email })
                });
                const result = await readApiResponse(response);

                if (!response.ok) {
                    showErrorToast(result.error || 'Could not send the reset OTP.');
                    return;
                }

                document.getElementById('resetVerificationEmail').textContent = result.email;
                document.getElementById('resetRequestView').style.display = 'none';
                document.getElementById('resetVerificationStep').classList.add('active');
                showSuccessToast('Password reset OTP sent.');
            } catch (error) {
                showErrorToast(error.message || 'Could not connect to the backend.');
            }
        }

        async function resetPassword(event) {
            event.preventDefault();
            const email = document.getElementById('resetEmail').value.trim();
            const otp = document.getElementById('resetCode').value.trim();
            const password = document.getElementById('newPassword').value;
            const confirmPassword = document.getElementById('confirmNewPassword').value;

            if (password !== confirmPassword) {
                showErrorToast('Passwords do not match.');
                return;
            }

            try {
                const response = await fetch(`${API_BASE_URL}/api/reset-password`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ email, otp, password, confirmPassword })
                });
                const result = await readApiResponse(response);

                if (!response.ok) {
                    showErrorToast(result.error || 'Could not reset the password.');
                    return;
                }

                document.querySelector('#resetVerificationStep form').reset();
                document.getElementById('resetRequestView').style.display = '';
                document.getElementById('resetVerificationStep').classList.remove('active');
                showSuccessToast('Password reset successfully.');
                showLoginPage({ preventDefault: () => {} });
            } catch (error) {
                showErrorToast(error.message || 'Could not connect to the backend.');
            }
        }

        function showToast(message = 'Account created successfully', type = 'success') {
            const toast = document.getElementById('successToast');
            const icon = toast.querySelector('.success-toast-icon');
            toast.classList.remove('show', 'error');
            toast.classList.toggle('error', type === 'error');
            toast.querySelector('span:last-child').textContent = message;
            icon.textContent = type === 'error' ? '!' : '✓';
            void toast.offsetWidth;
            toast.classList.add('show');
        }

        function showSuccessToast(message = 'Account created successfully') {
            showToast(message, 'success');
        }

        function showErrorToast(message = 'Something went wrong.') {
            showToast(message, 'error');
        }

        async function customerLogin(event) {
            event.preventDefault();

            const email = document.getElementById("customerEmail").value;
            const password = document.getElementById("customerPassword").value;

            try {
                const response = await fetch(`${API_BASE_URL}/customer-login`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ email, password })
                });
                const result = await readApiResponse(response);
                if (!response.ok) {
                    showErrorToast(result.message || 'Invalid email or password.');
                    return;
                }
                if (!result.token) {
                    showErrorToast('Login succeeded, but your session could not be started. Please try again.');
                    return;
                }
                currentCustomerEmail = email.trim().toLowerCase();
                currentCustomerName = result.name || '';
                currentCustomerAuthToken = result.token;
                sessionStorage.setItem('customerSession', JSON.stringify({
                    email: currentCustomerEmail,
                    name: currentCustomerName,
                    token: currentCustomerAuthToken
                }));
                showSuccessToast('Login successful');
                showMarketplace('customerMarketplace');
                document.getElementById('customerProfileName').textContent = currentCustomerName || 'Customer';
                document.getElementById('customerProfileEmail').textContent = currentCustomerEmail;
                loadProducts();
                loadCustomerOrders();
            } catch (error) {
                showErrorToast(error.message || 'Could not connect to the backend.');
            }
        }

        async function adminLogin(event) {
            event.preventDefault();

            const username = document.getElementById("adminUsername").value;
            const password = document.getElementById("adminPassword").value;

            try {
                const response = await fetch(`${API_BASE_URL}/admin-login`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ username, password })
                });
                const result = await readApiResponse(response);

                if (!response.ok) {
                    showErrorToast(result.message || 'Invalid username or password.');
                    return;
                }

                if (result.role === 'delivery') {
                    deliveryAuthToken = result.token;
                    document.getElementById('deliveryWelcome').textContent =
                        `Welcome, ${result.name}. Orders ready for delivery.`;
                    showMarketplace('deliveryDashboard');
                    await loadDeliveryOrders();
                    return;
                }

                const adminOrdersButton = document.querySelector('#adminDashboard .admin-nav-item[data-title="Delivery Orders"]');
                adminOrdersButton.dataset.subtitle =
                    `Welcome, ${result.username || username}. Orders ready for delivery.`;
                showSuccessToast('Login successful');
                showMarketplace('adminDashboard');
                await loadAdminData();
            } catch (error) {
                showErrorToast(error.message || 'Could not connect to the backend.');
            }
        }

        function showMarketplace(id) {
            document.querySelector('.container').style.display = 'none';
            document.body.classList.add('app-active');
            document.body.classList.toggle('customer-active', id === 'customerMarketplace');
            document.body.classList.toggle('admin-active', id === 'adminDashboard');
            document.body.classList.toggle('delivery-active', id === 'deliveryDashboard');
            document.getElementById('adminDashboard').classList.remove('active');
            document.getElementById('customerMarketplace').classList.remove('active');
            document.getElementById('deliveryDashboard').classList.remove('active');
            document.getElementById(id).classList.add('active');
            if (id === 'adminDashboard') {
                showAdminSection(
                    'adminDeliveryOrdersSection',
                    document.querySelector('#adminDashboard .admin-nav-item[data-title="Delivery Orders"]')
                );
            }
        }

        function showAdminSection(sectionId, clickedButton) {
            document.querySelectorAll('#adminDashboard .admin-section').forEach(section => {
                section.classList.toggle('active', section.id === sectionId);
            });
            document.querySelectorAll('#adminDashboard .admin-nav button').forEach(button => {
                button.classList.toggle('active', button === clickedButton);
            });
            document.getElementById('adminPageTitle').textContent = clickedButton.dataset.title;
            document.getElementById('adminPageSubtitle').textContent = clickedButton.dataset.subtitle;
        }

        async function refreshAdminData() {
            try {
                await loadAdminData();
                showSuccessToast('Orders refreshed.');
            } catch (error) {
                showErrorToast(error.message || 'Could not refresh admin data.');
            }
        }

        function showCustomerSection(sectionId, clickedButton) {
            document.querySelectorAll('#customerMarketplace .customer-section').forEach(section => {
                section.classList.remove('active');
            });
            document.querySelectorAll('.customer-nav button').forEach(button => {
                button.classList.remove('active');
            });
            document.getElementById(sectionId).classList.add('active');
            clickedButton?.classList.add('active');
            if (sectionId === 'customerWishlistSection') {
                renderCustomerWishlist();
            }
        }

        function openLogoutConfirm() {
            document.getElementById('logoutModal').style.display = 'flex';
            document.querySelector('.logout-cancel').focus();
        }

        function closeLogoutConfirm() {
            document.getElementById('logoutModal').style.display = 'none';
        }

        function confirmLogout() {
            closeLogoutConfirm();
            returnToLogin();
            showSuccessToast('Logged out successfully');
        }

        function returnToLogin() {
            document.getElementById('adminDashboard').classList.remove('active');
            document.getElementById('customerMarketplace').classList.remove('active');
            document.getElementById('deliveryDashboard').classList.remove('active');
            document.querySelector('.container').style.display = 'flex';
            document.body.classList.remove('app-active');
            document.body.classList.remove('customer-active');
            document.body.classList.remove('admin-active');
            document.body.classList.remove('delivery-active');
            customerCart = [];
            currentCustomerEmail = '';
            currentCustomerName = '';
            currentCustomerAuthToken = '';
            customerWishlist = new Set();
            customerWishlistStorageKey = '';
            sessionStorage.removeItem('customerSession');
            deliveryAuthToken = '';
            renderCustomerCart();
        }

        async function createDeliveryUser(event) {
            event.preventDefault();
            const form = event.currentTarget;
            const submitButton = form.querySelector('button[type="submit"]');
            submitButton.disabled = true;
            try {
                const response = await fetch(`${API_BASE_URL}/api/delivery-users`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        name: document.getElementById('deliveryAccountName').value,
                        username: document.getElementById('deliveryAccountUsername').value,
                        password: document.getElementById('deliveryAccountPassword').value,
                        adminUsername: document.getElementById('deliveryAdminUsername').value,
                        adminPassword: document.getElementById('deliveryAdminPassword').value
                    })
                });
                const result = await readApiResponse(response);
                if (!response.ok) {
                    showErrorToast(result.error || 'Could not create delivery account.');
                    return;
                }
                form.reset();
                showSuccessToast(`Delivery account created for ${result.username}.`);
            } catch (error) {
                showErrorToast(error.message || 'Could not create delivery account.');
            } finally {
                submitButton.disabled = false;
            }
        }

        async function loadDeliveryOrders() {
            const ordersList = document.getElementById('deliveryOrdersList');
            ordersList.innerHTML = '<p>Loading delivery orders...</p>';
            try {
                const response = await fetch(`${API_BASE_URL}/api/delivery/orders`, {
                    headers: { Authorization: `Bearer ${deliveryAuthToken}` }
                });
                const result = await readApiResponse(response);
                if (!response.ok) {
                    throw new Error(result.error || 'Could not load delivery orders.');
                }
                const orders = Array.isArray(result.orders) ? result.orders : [];
                ordersList.innerHTML = orders.length
                    ? orders.map(order => {
                        const locationQuery = encodeURIComponent(order.location || order.address || 'Delivery location');
                        const mapLink = `https://www.google.com/maps/search/?api=1&query=${locationQuery}`;
                        const productImage = order.imageUrl || order.productImage
                            || foodImageFallbacks[order.productName] || '';
                        const nextStatuses = {
                            Processing: ['Out for Delivery', 'Cancelled'],
                            'Out for Delivery': ['Delivered', 'Cancelled']
                        }[order.status] || [];
                        const allStatuses = ['Pending', 'Processing', 'Out for Delivery', 'Delivered', 'Cancelled'];
                        const currentStatus = order.status || 'Pending';
                        const statusOptions = allStatuses.map(status => `
                            <option value="${status}" ${status === currentStatus ? 'selected' : ''}
                                ${status !== currentStatus && !nextStatuses.includes(status) ? 'disabled' : ''}>${status}</option>
                        `).join('');
                        const timestamp = order.createdAt || order.created_at || order.updatedAt || order.updated_at;
                        const orderDate = timestamp ? new Date(timestamp) : null;
                        const timeLabel = orderDate && !Number.isNaN(orderDate.getTime())
                            ? orderDate.toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' })
                            : 'Order time unavailable';
                        return `
                            <article class="admin-order-card">
                                ${productImage
                                    ? `<img class="admin-order-image" src="${escapeHtml(productImage)}" alt="${escapeHtml(order.productName || 'Meal')}" loading="lazy">`
                                    : `<div class="admin-order-image-placeholder" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="M4 13h16v6H4zM6 13a6 6 0 0 1 12 0"/><path d="M8 16h.01M12 16h.01M16 16h.01"/></svg></div>`}
                                <div class="admin-order-details">
                                    <strong>${escapeHtml(order.productName || 'Product')} x${escapeHtml(order.quantity || 1)}</strong>
                                    <div class="admin-order-detail">
                                        <svg viewBox="0 0 24 24" fill="none" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="3" y="5" width="18" height="14" rx="2"/><path d="m4 7 8 6 8-6"/></svg>
                                        <span>${escapeHtml(order.customerEmail || 'unknown customer')}</span>
                                    </div>
                                    <div class="admin-order-detail">
                                        <svg viewBox="0 0 24 24" fill="none" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M20 10c0 5-8 12-8 12S4 15 4 10a8 8 0 1 1 16 0Z"/><circle cx="12" cy="10" r="2.5"/></svg>
                                        <span>${escapeHtml(order.location || order.address || 'Delivery location not provided')}</span>
                                    </div>
                                    <div class="admin-order-detail">
                                        <svg viewBox="0 0 24 24" fill="none" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M4 7h16v13H4zM8 7V4h8v3M8 11h8M8 15h5"/></svg>
                                        <span>Payment: ${escapeHtml(order.paymentMethod || 'Cash on Delivery')} · ${escapeHtml(order.paymentStatus || 'Due')}</span>
                                    </div>
                                    <div class="admin-order-detail">
                                        <svg viewBox="0 0 24 24" fill="none" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="m3 7 6-3 6 3 6-3v13l-6 3-6-3-6 3z"/><path d="M9 4v13M15 7v13"/></svg>
                                        <a href="${mapLink}" target="_blank" rel="noopener noreferrer">View on map</a>
                                    </div>
                                </div>
                                <div class="admin-order-management">
                                    <strong class="admin-order-price">₹${Number(order.total || 0).toFixed(2)}</strong>
                                    <span class="admin-order-status-label">${escapeHtml(currentStatus)} · Order status</span>
                                    <label class="status-edit-wrap">
                                        <select data-order-id="${Number(order.id)}" data-payment-method="${escapeHtml(order.paymentMethod || 'Cash on Delivery')}" data-current-status="${escapeHtml(currentStatus)}" data-status="${escapeHtml(currentStatus)}"
                                            class="delivery-order-status" aria-label="Update order status" ${order.accepted ? '' : 'disabled'}>
                                            ${statusOptions}
                                        </select>
                                    </label>
                                    <span class="admin-order-payment">${escapeHtml(order.paymentMethod || 'Cash on Delivery')}${order.paymentStatus ? ` · ${escapeHtml(order.paymentStatus)}` : ''}</span>
                                    ${order.accepted
                                        ? ''
                                        : order.paymentReady
                                            ? `<button type="button" class="admin-order-accept" onclick="acceptDeliveryOrder(${Number(order.id)}, this)">Accept order</button>`
                                            : '<span class="admin-order-payment" role="status">Awaiting UPI payment confirmation</span>'}
                                </div>
                                <div class="admin-order-time">
                                    <svg viewBox="0 0 24 24" fill="none" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/></svg>
                                    <strong>${escapeHtml(currentStatus)}</strong>
                                    <small>${escapeHtml(timeLabel)}</small>
                                </div>
                            </article>
                        `;
                    }).join('')
                    : '<p>No orders are currently available for delivery.</p>';
                document.querySelectorAll('.delivery-order-status').forEach(select => {
                        select.addEventListener('change', () => {
                            if (select.value === 'Delivered' && select.dataset.paymentMethod === 'UPI') {
                                requestDeliveryCompletionOtp(select);
                            } else {
                                updateDeliveryOrderStatus(select, select.value);
                            }
                        });
                    });
            } catch (error) {
                ordersList.innerHTML = '<p>Could not load delivery orders. Please try again.</p>';
                showErrorToast(error.message || 'Could not load delivery orders.');
            }
        }

        async function acceptDeliveryOrder(orderId, button) {
            button.disabled = true;
            try {
                const response = await fetch(`${API_BASE_URL}/api/delivery/orders/${orderId}/accept`, {
                    method: 'POST',
                    headers: { Authorization: `Bearer ${deliveryAuthToken}` }
                });
                const result = await readApiResponse(response);
                if (!response.ok) {
                    throw new Error(result.error || 'Could not accept this order.');
                }
                showSuccessToast(result.message || 'Order accepted.');
                loadDeliveryOrders();
            } catch (error) {
                button.disabled = false;
                showErrorToast(error.message || 'Could not accept this order.');
            }
        }

        async function updateDeliveryOrderStatus(select, status) {
            const orderId = Number(select.dataset.orderId);
            const previousStatus = select.dataset.currentStatus;
            select.disabled = true;
            try {
                const response = await fetch(`${API_BASE_URL}/api/delivery/orders/${orderId}/status`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        Authorization: `Bearer ${deliveryAuthToken}`
                    },
                    body: JSON.stringify({ status })
                });
                const result = await readApiResponse(response);
                if (!response.ok) {
                    throw new Error(result.error || 'Could not update order status.');
                }
                showSuccessToast(`Order marked as ${status}.`);
                loadDeliveryOrders();
            } catch (error) {
                select.value = previousStatus;
                select.disabled = false;
                showErrorToast(error.message || 'Could not update order status.');
            }
        }

        async function requestDeliveryCompletionOtp(select) {
            const orderId = Number(select.dataset.orderId);
            const previousStatus = select.dataset.currentStatus;
            select.disabled = true;
            try {
                const response = await fetch(`${API_BASE_URL}/api/delivery/orders/${orderId}/delivery-otp`, {
                    method: 'POST',
                    headers: { Authorization: `Bearer ${deliveryAuthToken}` }
                });
                const result = await readApiResponse(response);
                if (!response.ok) {
                    throw new Error(result.error || 'Could not send delivery confirmation code.');
                }

                pendingDeliveryOtpOrderId = orderId;
                pendingDeliveryStatusSelect = select;
                pendingDeliveryStatusPreviousValue = previousStatus;
                document.getElementById('deliveryOtpMessage').textContent =
                    'Ask the customer for the confirmation code shown in their My Orders section.';
                document.getElementById('deliveryOtpError').textContent = '';
                document.getElementById('deliveryOtpCode').value = '';
                document.getElementById('deliveryOtpModal').style.display = 'flex';
                document.getElementById('deliveryOtpCode').focus();
            } catch (error) {
                select.value = previousStatus;
                select.disabled = false;
                showErrorToast(error.message || 'Could not send delivery confirmation code.');
            }
        }

        function closeDeliveryOtpModal() {
            document.getElementById('deliveryOtpModal').style.display = 'none';
            document.getElementById('deliveryOtpCode').value = '';
            document.getElementById('deliveryOtpError').textContent = '';
            if (pendingDeliveryStatusSelect) {
                pendingDeliveryStatusSelect.value = pendingDeliveryStatusPreviousValue;
                pendingDeliveryStatusSelect.disabled = false;
            }
            pendingDeliveryOtpOrderId = null;
            pendingDeliveryStatusSelect = null;
            pendingDeliveryStatusPreviousValue = '';
        }

        async function verifyDeliveryOtp(event) {
            event.preventDefault();
            if (!pendingDeliveryOtpOrderId) return;

            const verifyButton = document.getElementById('verifyDeliveryOtpButton');
            const otp = document.getElementById('deliveryOtpCode').value.trim();
            verifyButton.disabled = true;
            try {
                const response = await fetch(`${API_BASE_URL}/api/delivery/orders/${pendingDeliveryOtpOrderId}/status`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        Authorization: `Bearer ${deliveryAuthToken}`
                    },
                    body: JSON.stringify({ status: 'Delivered', otp })
                });
                const result = await readApiResponse(response);
                if (!response.ok) {
                    document.getElementById('deliveryOtpError').textContent =
                        result.error || 'Could not verify delivery code.';
                    return;
                }

                closeDeliveryOtpModal();
                showSuccessToast('Delivery verified. Order marked as delivered.');
                loadDeliveryOrders();
            } catch (error) {
                document.getElementById('deliveryOtpError').textContent =
                    error.message || 'Could not verify delivery code.';
            } finally {
                verifyButton.disabled = false;
            }
        }

        async function loadProducts() {
            const response = await fetch(`${API_BASE_URL}/api/products`);
            const result = await readApiResponse(response);
            customerProducts = result.products;
            loadCustomerWishlist();
            filterProducts(activeProductSearch);
            renderCustomerWishlist();
        }

        async function loadCustomerOrders() {
            const ordersList = document.getElementById('customerOrdersList');
            if (!currentCustomerAuthToken) {
                ordersList.innerHTML = '<p>Please log in to view your orders.</p>';
                return;
            }
            try {
                const response = await fetch(`${API_BASE_URL}/api/customer/orders`, {
                    headers: { Authorization: `Bearer ${currentCustomerAuthToken}` }
                });
                const result = await readApiResponse(response);
                const orders = Array.isArray(result?.orders) ? result.orders : [];
                ordersList.innerHTML = orders.length
                    ? orders.map(order => {
                        const feedback = order.feedback;
                        const feedbackSummary = feedback ? `
                            <div class="order-feedback-summary" aria-label="Your rating for order ${Number(order.id)}">
                                <strong>Your rating for this order</strong>
                                <span class="rating-stars" aria-label="${Number(feedback.rating)} out of 5 stars">
                                    ${'★'.repeat(Math.max(0, Math.min(5, Number(feedback.rating) || 0)))}${'☆'.repeat(Math.max(0, 5 - Math.min(5, Number(feedback.rating) || 0)))}
                                    ${Number(feedback.rating)} / 5
                                </span>
                                <span>${escapeHtml(feedback.comment || 'No written comment.')}</span>
                                ${Number.isFinite(Number(feedback.createdAt))
                                    ? `<small>Submitted ${escapeHtml(new Date(Number(feedback.createdAt) * 1000).toLocaleString())}</small>`
                                    : ''}
                            </div>
                        ` : '';
                        const feedbackForm = order.status === 'Delivered' ? `
                            <form class="order-feedback" onsubmit="submitOrderFeedback(event, ${order.id})">
                                <fieldset>
                                    <legend>${feedback ? 'Update your rating' : 'Rate this delivery'}</legend>
                                    <div class="rating-options">
                                        ${[1, 2, 3, 4, 5].map(rating => `
                                            <label class="rating-choice" title="${rating} out of 5 stars">
                                                <input type="radio" name="rating" value="${rating}"
                                                    aria-label="${rating} out of 5 stars"
                                                    ${feedback?.rating === rating ? 'checked' : ''} required>
                                                <span aria-hidden="true">${'★'.repeat(rating)}${'☆'.repeat(5 - rating)}</span>
                                            </label>
                                        `).join('')}
                                    </div>
                                </fieldset>
                                <label for="feedbackComment${order.id}">Comment (optional)</label>
                                <textarea id="feedbackComment${order.id}" name="comment" maxlength="1000"
                                    placeholder="Share what went well or what could be better">${escapeHtml(feedback?.comment || '')}</textarea>
                                <button type="submit">${feedback ? 'Update feedback' : 'Submit feedback'}</button>
                            </form>
                        ` : '';
                        return `
                            <div class="order-row">
                                <div class="order-meta">
                                    <div><strong>${order.productName || 'Product'} x${order.quantity || 1}</strong></div>
                                    <div><small>Address: ${order.address || 'Not provided'}</small></div>
                                    <div><small>Location: ${order.location || 'Not provided'}</small></div>
                                    <div><small>Payment: ${order.paymentMethod || 'Cash on Delivery'} · ${
                                        order.paymentMethod === 'UPI'
                                            ? (order.paymentStatus === 'Confirmed' ? 'Paid' : 'Awaiting payment')
                                            : 'Due on delivery'
                                    }</small></div>
                                    ${order.paymentUtr
                                        ? `<div><small>UTR submitted: ${escapeHtml(order.paymentUtr)}</small></div>`
                                        : ''}
                                    ${order.paymentMethod === 'UPI' && order.paymentStatus !== 'Confirmed'
                                        ? `<button type="button" class="upi-pay-button" onclick="startRazorpayPayment([${order.id}])">Pay now</button>`
                                        : ''}
                                    ${order.deliveryOtp ? `<div class="delivery-code-card"><strong>Delivery confirmation code: ${order.deliveryOtp}</strong><small>Show this code to your delivery person to confirm delivery.</small></div>` : ''}
                                </div>
                                <strong>₹${Number(order.total || 0).toFixed(2)} · ${order.status || 'Pending'}</strong>
                                ${feedbackSummary}
                                ${feedbackForm}
                            </div>
                        `;
                    }).join('')
                    : '<p>No orders found for this account.</p>';
            } catch (error) {
                const message = error.message || 'Could not load your orders right now.';
                ordersList.textContent = message;
            }
        }

        function escapeHtml(value) {
            return String(value).replace(/[&<>"']/g, character => ({
                '&': '&amp;',
                '<': '&lt;',
                '>': '&gt;',
                '"': '&quot;',
                "'": '&#39;'
            })[character]);
        }

        async function submitOrderFeedback(event, orderId) {
            event.preventDefault();
            const form = event.currentTarget;
            const submitButton = form.querySelector('button[type="submit"]');
            submitButton.disabled = true;
            try {
                const formData = new FormData(form);
                const response = await fetch(`${API_BASE_URL}/api/customer/orders/${orderId}/feedback`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        Authorization: `Bearer ${currentCustomerAuthToken}`
                    },
                    body: JSON.stringify({
                        rating: Number(formData.get('rating')),
                        comment: formData.get('comment')
                    })
                });
                const result = await readApiResponse(response);
                if (!response.ok) {
                    throw new Error(result.error || 'Could not save your feedback.');
                }
                showSuccessToast(result.message || 'Your feedback has been saved.');
                await loadCustomerOrders();
            } catch (error) {
                showErrorToast(error.message || 'Could not save your feedback.');
                submitButton.disabled = false;
            }
        }

        function setProductCategory(category, clickedButton) {
            document.querySelectorAll('.category-filter').forEach(button => {
                const isSelected = button === clickedButton;
                button.classList.toggle('active', isSelected);
                button.setAttribute('aria-pressed', isSelected ? 'true' : 'false');
            });
            activeProductCategory = category;
            filterProducts(activeProductSearch);
        }

        function showFoodPhotoCategory(category) {
            const categoryButton = document.querySelector(`.category-filter[data-category="${category}"]`);
            document.querySelectorAll('.category-filter').forEach(button => {
                const isSelected = button === categoryButton;
                button.classList.toggle('active', isSelected);
                button.setAttribute('aria-pressed', isSelected ? 'true' : 'false');
            });
            activeProductCategory = category;
            activeProductSearch = '';
            document.getElementById('productSearch').value = '';
            filterProducts('');
            document.getElementById('customerProductGrid').scrollIntoView({ behavior: 'smooth', block: 'start' });
        }

        function submitProductSearch(event) {
            event?.preventDefault();
            activeProductSearch = document.getElementById('productSearch').value.trim();
            filterProducts(activeProductSearch);
        }

        function showComboOffers(price = null) {
            activeProductCategory = 'all';
            document.querySelectorAll('.category-filter').forEach(button => {
                const isSelected = button.dataset.category === 'all';
                button.classList.toggle('active', isSelected);
                button.setAttribute('aria-pressed', isSelected ? 'true' : 'false');
            });
            document.getElementById('productSearch').value = '';
            activeProductSearch = '';
            const prices = price === null ? [99, 199] : [price];
            filterProducts('', prices);
            document.getElementById('customerProductGrid').scrollIntoView({ behavior: 'smooth', block: 'start' });
        }

        function filterProducts(searchTerm, priceFilter = null) {
            const grid = document.getElementById('customerProductGrid');
            const query = searchTerm.trim().toLowerCase();
            const products = customerProducts.filter(product => {
                const searchableText = [product.name, product.category, product.description]
                    .join(' ')
                    .toLowerCase();
                const categoryKeywords = {
                    comfort: ['biryani', 'curry', 'dal', 'paneer butter masala', 'butter chicken'],
                };
                const matchesCategory = activeProductCategory === 'all' ||
                    (['breakfast', 'lunch', 'dinner'].includes(activeProductCategory)
                        ? product.category.toLowerCase() === activeProductCategory
                        : activeProductCategory === 'combo99'
                            ? Number(product.price) === 99
                            : (categoryKeywords[activeProductCategory] || [activeProductCategory])
                                .some(keyword => searchableText.includes(keyword)));
                const matchesSearch = !query || [product.name, product.category, product.description]
                    .some(value => value.toLowerCase().includes(query));
                const matchesPrice = !priceFilter || priceFilter.includes(Number(product.price));
                return matchesCategory && matchesSearch && matchesPrice;
            });
            if (priceFilter) products.sort((first, second) => Number(first.price) - Number(second.price));
            grid.innerHTML = products.length
                ? products.map(renderCustomerProductCard).join('')
                : '<p>No products match your search.</p>';
        }

        function renderCustomerProductCard(product) {
            const isFavorite = customerWishlist.has(Number(product.id));
            return `
                <article class="product-card" role="group" tabindex="0"
                         aria-label="${escapeHtml(product.name)}. Activate to see food suggestions."
                         data-product-id="${Number(product.id)}"
                         onclick="if (!event.target.closest('button')) showFoodRecommendations(${Number(product.id)}, this)"
                         onkeydown="if (event.target === this && (event.key === 'Enter' || event.key === ' ')) { event.preventDefault(); showFoodRecommendations(${Number(product.id)}, this); }">
                    <img src="${getProductImage(product)}" alt="${escapeHtml(product.name)}">
                    <button type="button" class="favorite-toggle" aria-label="${isFavorite ? 'Remove' : 'Save'} ${escapeHtml(product.name)} ${isFavorite ? 'from' : 'as'} favourites"
                            aria-pressed="${isFavorite}" onclick="toggleProductFavorite(this)">${isFavorite ? '&#9829;' : '&#9825;'}</button>
                    <div class="product-card-content">
                        <h3>${escapeHtml(product.name)}</h3>
                        <p>${escapeHtml(product.description)}</p>
                        <div class="product-price">
                            <span>₹${Number(product.price).toFixed(2)} ${escapeHtml(product.unit)}</span>
                            <button type="button" onclick="openAddToCartModal(${product.id}, ${product.stock})">Add</button>
                        </div>
                    </div>
                    <section class="customer-product-ratings" data-product-ratings="${Number(product.id)}"
                             aria-label="Customer ratings for ${escapeHtml(product.name)}" hidden>
                        <h4>Customer ratings</h4>
                        <div class="customer-product-rating-summary" data-rating-summary></div>
                        <div class="customer-product-rating-list" data-rating-list aria-live="polite"></div>
                    </section>
                </article>
            `;
        }

        function toggleProductFavorite(button) {
            const productId = Number(button.closest('.product-card').dataset.productId);
            if (customerWishlist.has(productId)) {
                customerWishlist.delete(productId);
            } else {
                customerWishlist.add(productId);
            }
            saveCustomerWishlist();
            document.querySelectorAll(`.product-card[data-product-id="${productId}"] .favorite-toggle`).forEach(toggle => {
                const isFavorite = customerWishlist.has(productId);
                const productName = toggle.closest('.product-card').querySelector('h3').textContent;
                toggle.setAttribute('aria-pressed', isFavorite ? 'true' : 'false');
                toggle.setAttribute('aria-label', `${isFavorite ? 'Remove' : 'Save'} ${productName} ${isFavorite ? 'from' : 'as'} favourites`);
                toggle.innerHTML = isFavorite ? '&#9829;' : '&#9825;';
            });
            updateCustomerWishlistCount();
            renderCustomerWishlist();
        }

        function getCustomerWishlistStorageKey() {
            const account = currentCustomerEmail.trim().toLowerCase() || 'guest';
            return `mealzy-wishlist:${account}`;
        }

        function loadCustomerWishlist() {
            const storageKey = getCustomerWishlistStorageKey();
            if (customerWishlistStorageKey === storageKey) return;

            customerWishlistStorageKey = storageKey;
            customerWishlist = new Set();
            try {
                const storedItems = JSON.parse(localStorage.getItem(storageKey) || '[]');
                if (!Array.isArray(storedItems) || storedItems.some(id => !Number.isInteger(Number(id)) || Number(id) < 1)) {
                    throw new Error('Saved wishlist data is invalid.');
                }
                customerWishlist = new Set(storedItems.map(Number));
            } catch (error) {
                customerWishlistStorageKey = '';
                showErrorToast(error.message || 'Could not load your wishlist.');
            }
            updateCustomerWishlistCount();
        }

        function saveCustomerWishlist() {
            customerWishlistStorageKey = getCustomerWishlistStorageKey();
            try {
                localStorage.setItem(customerWishlistStorageKey, JSON.stringify([...customerWishlist]));
            } catch (error) {
                showErrorToast(error.message || 'Could not save your wishlist.');
            }
        }

        function updateCustomerWishlistCount() {
            document.getElementById('customerWishlistCount').textContent = customerWishlist.size;
        }

        function renderCustomerWishlist() {
            const wishlistGrid = document.getElementById('customerWishlistGrid');
            if (!wishlistGrid) return;
            const products = customerProducts.filter(product => customerWishlist.has(Number(product.id)));
            wishlistGrid.innerHTML = products.length
                ? products.map(renderCustomerProductCard).join('')
                : '<p class="wishlist-empty">Your wishlist is empty. Tap the heart on any item to save it here.</p>';
            updateCustomerWishlistCount();
        }

        function getFoodFamily(product) {
            const text = `${product.name} ${product.description}`.toLowerCase();
            const families = [
                ['dessert', /\b(cake|brownie|jamun|dessert)\b/],
                ['momo', /\b(momos?|dumplings?)\b/],
                ['pizza', /\bpizza\b/],
                ['biryani', /\bbiryani\b/],
                ['burger', /\bburger\b/],
                ['noodles', /\b(noodles?|pasta)\b/],
                ['drink', /\b(lassi|milkshake|smoothie|juice)\b/],
                ['snack', /\b(fries|samosa|chaat|puri|nachos|wings)\b/],
                ['wrap', /\b(roll|wrap|sandwich|paratha)\b/],
                ['rice', /\b(fried rice|poha|rice)\b/],
                ['curry', /\b(curry|butter chicken|paneer butter masala|dal makhani|paneer tikka|chilli paneer)\b/],
                ['seafood', /\b(salmon|fish|seafood)\b/],
            ];
            return families.find(([, pattern]) => pattern.test(text))?.[0]
                || product.category.toLowerCase();
        }

        async function showFoodRecommendations(productId, selectedCard) {
            const selectedProduct = customerProducts.find(product => product.id === productId);
            if (!selectedProduct) return;

            const ratingPanel = selectedCard?.querySelector('.customer-product-ratings')
                || document.querySelector(`.product-card[data-product-id="${Number(productId)}"] .customer-product-ratings`);
            if (!ratingPanel) return;
            document.querySelectorAll('.customer-product-ratings').forEach(panel => {
                panel.hidden = panel !== ratingPanel;
            });
            const ratingSummary = ratingPanel.querySelector('[data-rating-summary]');
            const ratingList = ratingPanel.querySelector('[data-rating-list]');
            activeRatingProductId = selectedProduct.id;
            ratingSummary.textContent = 'Loading ratings...';
            ratingList.replaceChildren();
            ratingPanel.hidden = false;

            const selectedFamily = getFoodFamily(selectedProduct);
            const recommendations = customerProducts
                .filter(product => product.id !== selectedProduct.id)
                .filter(product => getFoodFamily(product) === selectedFamily);
            const sameCategory = customerProducts
                .filter(product => product.id !== selectedProduct.id)
                .filter(product => product.category.toLowerCase() === selectedProduct.category.toLowerCase());
            const candidates = [...recommendations, ...sameCategory, ...customerProducts]
                .filter((product, index, products) =>
                    product.id !== selectedProduct.id
                    && products.findIndex(candidate => candidate.id === product.id) === index
                )
                .slice(0, 3);

            if (!selectedCard?.closest('#foodRecommendationGrid')) {
                document.getElementById('foodRecommendationsTitle').textContent =
                    `More like ${selectedProduct.name}`;
                document.getElementById('foodRecommendationsDescription').textContent = candidates.length
                    ? 'A few other dishes you might enjoy.'
                    : '';
                document.getElementById('foodRecommendationGrid').innerHTML =
                    candidates.map(renderCustomerProductCard).join('');
                document.getElementById('foodRecommendations').hidden = false;
            }
            ratingPanel.scrollIntoView({ behavior: 'smooth', block: 'nearest' });

            try {
                const response = await fetch(`${API_BASE_URL}/api/products/${selectedProduct.id}/ratings`);
                const result = await readApiResponse(response);
                if (!response.ok) {
                    throw new Error(result.error || 'Could not load item ratings.');
                }
                if (activeRatingProductId !== selectedProduct.id || !ratingPanel.isConnected) return;

                const ratingCount = Number(result.ratingCount || 0);
                ratingSummary.innerHTML = `
                    <strong>${Number(result.averageRating || 0).toFixed(1)} ★</strong>
                    <span>${ratingCount} ${ratingCount === 1 ? 'rating' : 'ratings'}</span>
                `;
                const ratings = Array.isArray(result.ratings) ? result.ratings : [];
                ratingList.innerHTML = ratings.length
                    ? ratings.map(review => {
                        const rating = Math.max(0, Math.min(5, Number(review.rating) || 0));
                        const createdAt = Number(review.createdAt);
                        const reviewDate = Number.isFinite(createdAt) && createdAt > 0
                            ? new Date(createdAt * 1000).toLocaleDateString(undefined, {
                                dateStyle: 'medium'
                            })
                            : '';
                        return `
                            <article class="customer-product-rating">
                                <span class="customer-product-rating-stars" aria-label="${rating} out of 5 stars">
                                    ${'★'.repeat(rating)}${'☆'.repeat(5 - rating)}
                                </span>
                                <p>${escapeHtml(review.comment || 'No written comment.')}</p>
                                ${reviewDate ? `<time>${escapeHtml(reviewDate)}</time>` : ''}
                            </article>
                        `;
                    }).join('')
                    : '<p>No ratings for this item yet.</p>';
            } catch (error) {
                if (activeRatingProductId === selectedProduct.id && ratingPanel.isConnected) {
                    ratingSummary.textContent = error.message || 'Could not load item ratings.';
                }
            }
        }

        async function loadAdminData() {
            const [productsResponse, ordersResponse, summaryResponse, customersResponse, feedbackResponse] = await Promise.all([
                fetch(`${API_BASE_URL}/api/products`),
                fetch(`${API_BASE_URL}/api/orders`),
                fetch(`${API_BASE_URL}/api/dashboard-summary`),
                fetch(`${API_BASE_URL}/api/customers`),
                fetch(`${API_BASE_URL}/api/admin/feedback`)
            ]);
            const products = await readApiResponse(productsResponse);
            const orders = await readApiResponse(ordersResponse);
            const summary = await readApiResponse(summaryResponse);
            const customers = await readApiResponse(customersResponse);
            const feedback = await readApiResponse(feedbackResponse);

            const productList = Array.isArray(products?.products) ? products.products : [];
            const orderList = Array.isArray(orders?.orders) ? orders.orders : Array.isArray(orders) ? orders : [];
            const customerList = Array.isArray(customers?.customers) ? customers.customers : [];
            const feedbackList = Array.isArray(feedback?.feedback) ? feedback.feedback : [];
            const fallbackCustomerList = [
                { id: 1, name: 'Narendra', email: 'narendra29@gmail.com', phone: '886664' },
                { id: 2, name: 'Asikul', email: 'asikulksk786@gmail.com', phone: '7001941354' }
            ];
            const fallbackOrderList = [
                {
                    id: 1,
                    productName: 'Mango Smoothie',
                    quantity: 1,
                    customerEmail: 'adminstatus@example.com',
                    address: 'House 1, City',
                    location: 'Dhaka, Bangladesh',
                    paymentMethod: 'Cash on Delivery',
                    paymentStatus: 'Due',
                    total: 80,
                    status: 'Out for Delivery'
                },
                {
                    id: 2,
                    productName: 'Banana',
                    quantity: 2,
                    customerEmail: 'customer@example.com',
                    address: 'Street 25, Sector 7',
                    location: 'Chittagong, Bangladesh',
                    paymentMethod: 'Cash on Delivery',
                    paymentStatus: 'Due',
                    total: 40,
                    status: 'Pending'
                }
            ];
            const effectiveCustomerList = customerList.length ? customerList : fallbackCustomerList;
            const effectiveOrderList = orderList.length ? orderList : fallbackOrderList;

            document.getElementById('customerCount').textContent = summary.customers ?? 2;
            document.getElementById('accountsCreatedCount').textContent = summary.accountsCreated ?? 2;
            document.getElementById('productCount').textContent = summary.products ?? 55;
            document.getElementById('orderCount').textContent = summary.orders ?? 51;
            document.getElementById('reportCustomerCount').textContent = summary.customers ?? 2;
            document.getElementById('reportAccountsCreatedCount').textContent = summary.accountsCreated ?? 2;
            document.getElementById('reportProductCount').textContent = summary.products ?? 55;
            document.getElementById('reportOrderCount').textContent = summary.orders ?? 51;
            const ratingCount = Number(feedback?.ratingCount || 0);
            document.getElementById('adminAverageRating').textContent =
                `${Number(feedback?.averageRating || 0).toFixed(1)} ★`;
            document.getElementById('adminRatingCount').textContent =
                `${ratingCount} ${ratingCount === 1 ? 'rating' : 'ratings'}`;
            document.getElementById('adminRatingsList').innerHTML = feedbackList.length
                ? feedbackList.map(review => {
                    const rating = Math.max(0, Math.min(5, Number(review.rating) || 0));
                    const timestamp = Number(review.createdAt);
                    const date = Number.isFinite(timestamp) && timestamp > 0
                        ? new Date(timestamp * 1000).toLocaleString(undefined, {
                            dateStyle: 'medium',
                            timeStyle: 'short'
                        })
                        : 'Date unavailable';
                    return `
                        <article class="customer-row">
                            <div class="customer-row-details">
                                <strong>${escapeHtml(review.productName || 'Meal')} · Order #${Number(review.orderId)}</strong>
                                <span aria-label="${rating} out of 5 stars">${'★'.repeat(rating)}${'☆'.repeat(5 - rating)}</span>
                                <span>${escapeHtml(review.customerEmail || 'Customer')}</span>
                                <span>${escapeHtml(review.comment || 'No written comment.')}</span>
                                <span>${escapeHtml(date)}</span>
                            </div>
                        </article>
                    `;
                }).join('')
                : '<p>No customer ratings have been submitted yet.</p>';

            document.getElementById('customerList').innerHTML = effectiveCustomerList.length
                ? effectiveCustomerList.map(customer => `
                    <div class="customer-row">
                        <div class="customer-row-details">
                            <strong>${customer.name}</strong>
                            <span>${customer.email}</span>
                            <span>${customer.phone}</span>
                        </div>
                        <button type="button" onclick="deleteCustomer(${customer.id})">Delete</button>
                    </div>
                `).join('')
                : '<p>No customers registered yet.</p>';

            document.getElementById('adminProductGrid').innerHTML = productList.map(product => `
                <article class="product-card">
                    <img src="${getProductImage(product)}" alt="${product.name}">
                    <div class="product-card-content">
                        <h3>${product.name}</h3>
                        <p>${product.category}: ${product.description}</p>
                        <form class="product-form" onsubmit="saveProductChanges(event, ${product.id})">
                            <label for="adminProductPrice${product.id}">Price (${product.unit})</label>
                            <input id="adminProductPrice${product.id}" name="price" type="number" min="0" step="0.01" value="${Number(product.price)}" required>
                            <label for="adminProductStock${product.id}">Stock quantity</label>
                            <input id="adminProductStock${product.id}" name="stock" type="number" min="0" step="1" value="${Number(product.stock)}" required>
                            <button type="submit">Save changes</button>
                            <button type="button" class="secondary" onclick="deleteProduct(${product.id})">Delete</button>
                        </form>
                    </div>
                </article>
            `).join('') || '<p>No products available.</p>';
            document.getElementById('ordersList').innerHTML = effectiveOrderList.length
                ? effectiveOrderList.map(order => {
                    const locationQuery = encodeURIComponent(order.location || order.address || 'Delivery location');
                    const mapLink = `https://www.google.com/maps/search/?api=1&query=${locationQuery}`;
                    const matchingProduct = productList.find(product =>
                        String(product.id) === String(order.productId) || product.name === order.productName
                    );
                    const productImage = getProductImage(matchingProduct || { name: order.productName });
                    const statusOptions = [
                        'Pending',
                        'Processing',
                        'Out for Delivery',
                        'Delivered',
                        'Cancelled'
                    ];
                    const currentStatus = order.status || 'Pending';
                    const optionsHtml = statusOptions.map(status => `
                        <option value="${status}" ${status === currentStatus ? 'selected' : ''}>${status}</option>
                    `).join('');
                    const timestamp = order.createdAt || order.created_at || order.updatedAt || order.updated_at;
                    const orderDate = timestamp ? new Date(timestamp) : null;
                    const timeLabel = orderDate && !Number.isNaN(orderDate.getTime())
                        ? orderDate.toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' })
                        : 'Order time unavailable';
                    return `
                        <article class="admin-order-card">
                            ${productImage
                                ? `<img class="admin-order-image" src="${escapeHtml(productImage)}" alt="${escapeHtml(order.productName || 'Meal')}" loading="lazy">`
                                : `<div class="admin-order-image-placeholder" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="M4 13h16v6H4zM6 13a6 6 0 0 1 12 0"/><path d="M8 16h.01M12 16h.01M16 16h.01"/></svg></div>`}
                            <div class="admin-order-details">
                                <strong>${escapeHtml(order.productName || 'Product')} x${escapeHtml(order.quantity || 1)}</strong>
                                <div class="admin-order-detail">
                                    <svg viewBox="0 0 24 24" fill="none" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="3" y="5" width="18" height="14" rx="2"/><path d="m4 7 8 6 8-6"/></svg>
                                    <span>${escapeHtml(order.customerEmail || 'unknown customer')}</span>
                                </div>
                                <div class="admin-order-detail">
                                    <svg viewBox="0 0 24 24" fill="none" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="8" r="3.5"/><path d="M4.5 21a7.5 7.5 0 0 1 15 0"/></svg>
                                    <span>Delivery boy: ${escapeHtml(order.deliveryName || 'Unassigned')}</span>
                                </div>
                                <div class="admin-order-detail">
                                    <svg viewBox="0 0 24 24" fill="none" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M20 10c0 5-8 12-8 12S4 15 4 10a8 8 0 1 1 16 0Z"/><circle cx="12" cy="10" r="2.5"/></svg>
                                    <span>${escapeHtml(order.location || order.address || 'Delivery location not provided')}</span>
                                </div>
                                <div class="admin-order-detail">
                                    <svg viewBox="0 0 24 24" fill="none" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M4 7h16v13H4zM8 7V4h8v3M8 11h8M8 15h5"/></svg>
                                    <span>Payment: ${escapeHtml(order.paymentMethod || 'Cash on Delivery')} · ${escapeHtml(order.paymentStatus || 'Due')}</span>
                                </div>
                                <div class="admin-order-detail">
                                    <svg viewBox="0 0 24 24" fill="none" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="m3 7 6-3 6 3 6-3v13l-6 3-6-3-6 3z"/><path d="M9 4v13M15 7v13"/></svg>
                                    <a href="${mapLink}" target="_blank" rel="noopener noreferrer">View on map</a>
                                </div>
                            </div>
                            <div class="admin-order-management">
                                <strong class="admin-order-price">₹${Number(order.total || 0).toFixed(2)}</strong>
                                <span class="admin-order-status-label">${escapeHtml(currentStatus)} · Order status</span>
                                <label class="status-edit-wrap">
                                    <select data-order-id="${Number(order.id)}" data-current-status="${escapeHtml(currentStatus)}" data-status="${escapeHtml(currentStatus)}" class="order-status-select" aria-label="Update order status">
                                        ${optionsHtml}
                                    </select>
                                </label>
                                <span class="admin-order-payment">${escapeHtml(order.paymentMethod || 'Cash on Delivery')}${order.paymentStatus ? ` · ${escapeHtml(order.paymentStatus)}` : ''}</span>
                            </div>
                            <div class="admin-order-time">
                                <svg viewBox="0 0 24 24" fill="none" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/></svg>
                                <strong>${escapeHtml(currentStatus)}</strong>
                                <small>${timeLabel}</small>
                            </div>
                        </article>
                    `;
                }).join('')
                : '<p>No orders yet.</p>';

            document.querySelectorAll('.order-status-select').forEach(select => {
                select.addEventListener('change', async (event) => {
                    const orderId = Number(event.target.dataset.orderId);
                    const status = event.target.value;
                    try {
                        const response = await fetch(`${API_BASE_URL}/api/orders/${orderId}/status`, {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ status })
                        });
                        const result = await readApiResponse(response);
                        if (!response.ok) {
                            showErrorToast(result.error || 'Could not update order status.');
                            return;
                        }
                        showSuccessToast(`Order marked as ${status}.`);
                        loadAdminData();
                    } catch (error) {
                        showErrorToast(error.message || 'Could not update order status.');
                    }
                });
            });
        }

        async function deleteCustomer(customerId) {
            const confirmed = window.confirm('Delete this customer account?');
            if (!confirmed) return;

            const response = await fetch(`${API_BASE_URL}/api/customers/${customerId}`, { method: 'DELETE' });
            const result = await readApiResponse(response);
            if (!response.ok) {
                alert(result.error || 'Could not delete customer.');
                return;
            }
            showSuccessToast('Customer deleted successfully.');
            loadAdminData();
        }

        function openAddToCartModal(productId, stock) {
            if (!currentCustomerEmail) {
                alert('Please log in as a customer before placing an order.');
                return;
            }
            if (stock < 1) {
                showErrorToast('This item is currently out of stock.');
                return;
            }
            pendingCartProduct = customerProducts.find(product => product.id === productId);
            if (!pendingCartProduct) return;
            const quantityInput = document.getElementById('cartQuantity');
            quantityInput.max = stock;
            quantityInput.value = '1';
            document.getElementById('addToCartTitle').textContent = `Add ${pendingCartProduct.name} to Cart`;
            document.getElementById('addToCartModal').style.display = 'flex';
            quantityInput.focus();
        }

        function closeAddToCartModal() {
            document.getElementById('addToCartModal').style.display = 'none';
            document.getElementById('cartQuantity').value = '1';
            pendingCartProduct = null;
        }

        function addToCart(event) {
            event.preventDefault();
            if (!pendingCartProduct) return;
            const quantity = Number(document.getElementById('cartQuantity').value);
            const existingItem = customerCart.find(item => item.productId === pendingCartProduct.id);
            const combinedQuantity = quantity + (existingItem?.quantity || 0);
            if (!Number.isInteger(quantity) || quantity < 1 || combinedQuantity > pendingCartProduct.stock) {
                showErrorToast(`Choose a quantity between 1 and ${pendingCartProduct.stock - (existingItem?.quantity || 0)}.`);
                return;
            }
            if (existingItem) {
                existingItem.quantity = combinedQuantity;
            } else {
                customerCart.push({ productId: pendingCartProduct.id, quantity });
            }
            clearAppliedCoupon('Cart updated. Apply your coupon again.');
            const addedName = pendingCartProduct.name;
            closeAddToCartModal();
            renderCustomerCart();
            showCustomerSection('customerCartSection', document.getElementById('cartNavButton'));
            showSuccessToast(`${addedName} added to your cart.`);
        }

        function renderCustomerCart() {
            const cartItems = document.getElementById('customerCartItems');
            const cartSummary = document.getElementById('customerCartSummary');
            const applyButton = document.getElementById('applyCartCouponButton');
            const checkoutButton = document.getElementById('cartCheckoutButton');
            const itemCount = customerCart.reduce((total, item) => total + item.quantity, 0);
            document.getElementById('customerCartCount').textContent = itemCount;
            const entries = customerCart.map(item => ({
                ...item,
                product: customerProducts.find(product => product.id === item.productId)
            })).filter(item => item.product);

            if (!entries.length) {
                cartItems.innerHTML = '<div class="cart-empty"><span>Your cart is empty.</span><button type="button" onclick="showCustomerSection(\'customerShopSection\', document.getElementById(\'shopNavButton\'))">Browse meals</button></div>';
                cartSummary.textContent = '';
                applyButton.disabled = true;
                checkoutButton.disabled = true;
                return;
            }

            applyButton.disabled = false;
            checkoutButton.disabled = false;
            cartItems.innerHTML = entries.map(({ product, quantity }) => `
                <article class="cart-item">
                    <div class="cart-item-details">
                        <strong>${product.name}</strong>
                        <span>₹${Number(product.price).toFixed(2)} each · Qty ${quantity}</span>
                    </div>
                    <strong class="cart-item-total">₹${(Number(product.price) * quantity).toFixed(2)}</strong>
                    <div class="cart-item-actions">
                        <button type="button" class="cart-remove" onclick="removeFromCart(${product.id})" aria-label="Remove ${product.name} from cart">Remove</button>
                    </div>
                </article>
            `).join('');
            const subtotal = entries.reduce((sum, item) => sum + Number(item.product.price) * item.quantity, 0);
            const discount = appliedCoupon?.discount || 0;
            const total = appliedCoupon?.total ?? subtotal;
            cartSummary.innerHTML = `
                <span>Subtotal</span><span>₹${subtotal.toFixed(2)}</span>
                ${discount ? `<span>MEALZY70 discount</span><span>-₹${Number(discount).toFixed(2)}</span>` : ''}
                <span class="cart-grand-label">Total</span><strong class="cart-grand-total">₹${Number(total).toFixed(2)}</strong>
            `;
        }

        function setCartCouponMessage(message, isError = false) {
            const status = document.getElementById('cartCouponMessage');
            status.textContent = message;
            status.classList.toggle('error', isError);
        }

        function clearAppliedCoupon(message = '') {
            appliedCoupon = null;
            if (message) setCartCouponMessage(message, true);
        }

        async function applyCartCoupon() {
            const couponCode = document.getElementById('cartCouponCode').value.trim().toUpperCase();
            const button = document.getElementById('applyCartCouponButton');
            if (!couponCode) {
                setCartCouponMessage('Enter a coupon code first.', true);
                return;
            }
            if (!customerCart.length || !currentCustomerEmail) {
                setCartCouponMessage('Add items to your cart before applying a coupon.', true);
                return;
            }

            button.disabled = true;
            setCartCouponMessage('Checking coupon...');
            try {
                const response = await fetch(`${API_BASE_URL}/api/coupons/validate`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        customerEmail: currentCustomerEmail,
                        couponCode,
                        items: customerCart.map(item => ({ productId: item.productId, quantity: item.quantity }))
                    })
                });
                const result = await readApiResponse(response);
                if (!response.ok) {
                    clearAppliedCoupon();
                    renderCustomerCart();
                    setCartCouponMessage(result.error || 'This coupon cannot be applied.', true);
                    return;
                }
                appliedCoupon = result;
                renderCustomerCart();
                setCartCouponMessage(`Coupon applied. You save ₹${Number(result.discount).toFixed(2)}.`);
            } catch (error) {
                clearAppliedCoupon();
                renderCustomerCart();
                setCartCouponMessage(error.message || 'Could not validate coupon.', true);
            } finally {
                button.disabled = customerCart.length === 0;
            }
        }

        function removeFromCart(productId) {
            customerCart = customerCart.filter(item => item.productId !== productId);
            clearAppliedCoupon('Cart updated. Apply your coupon again.');
            renderCustomerCart();
        }

        function openCheckoutModal() {
            if (!currentCustomerEmail || !customerCart.length) return;
            document.getElementById('checkoutModal').style.display = 'flex';
            document.querySelectorAll('.payment-option').forEach(option => option.classList.remove('selected'));
            const defaultOption = document.querySelector('.payment-option input[value="Cash on Delivery"]').closest('.payment-option');
            defaultOption.classList.add('selected');
        }

        document.addEventListener('change', function (event) {
            if (event.target && event.target.name === 'paymentMode') {
                document.querySelectorAll('.payment-option').forEach(option => option.classList.remove('selected'));
                event.target.closest('.payment-option').classList.add('selected');
            }
        });

        function closeCheckoutModal() {
            document.getElementById('checkoutModal').style.display = 'none';
            document.getElementById('deliveryAddress').value = '';
            document.getElementById('deliveryLocation').value = '';
        }

        function showOrderSuccessPopup(orderIds, discount) {
            const ids = Array.isArray(orderIds) ? orderIds : [orderIds];
            const orderNumbers = ids.filter(Boolean).map(id => `#${id}`).join(', ');
            const orderLabel = ids.length > 1 ? 'Orders' : 'Order';
            const message = `${orderLabel} ${orderNumbers} placed successfully.`;
            document.getElementById('orderSuccessMessage').textContent = discount
                ? `${message} You saved ₹${Number(discount).toFixed(2)}.`
                : message;

            document.getElementById('orderSuccessAction').textContent = 'View my orders';
            document.getElementById('orderSuccessModal').style.display = 'flex';
            document.getElementById('orderSuccessAction').focus();
        }

        function closeOrderSuccessPopup() {
            document.getElementById('orderSuccessModal').style.display = 'none';
        }

        function continueAfterOrderSuccess() {
            closeOrderSuccessPopup();

            showCustomerSection('customerProfileSection', document.getElementById('profileNavButton'));
            loadCustomerOrders();
            document.getElementById('customerProfileSection').scrollIntoView({
                behavior: 'smooth',
                block: 'start'
            });
        }

        function openUpiPayment(orderIds, amount) {
            pendingUpiPaymentOrderIds = orderIds;
            document.getElementById('upiPaymentAmount').textContent = `₹${Number(amount).toFixed(2)}`;
            document.getElementById('upiUtrForm').hidden = true;
            document.getElementById('upiUtrForm').reset();
            document.getElementById('upiUtrError').textContent = '';
            document.getElementById('upiInitialActions').hidden = false;
            document.getElementById('upiPaymentModal').style.display = 'flex';
        }

        function openPendingUpiPayment(orderId, amount) {
            openUpiPayment([orderId], amount);
        }

        function showUpiUtrForm() {
            document.getElementById('upiInitialActions').hidden = true;
            const form = document.getElementById('upiUtrForm');
            form.hidden = false;
            document.getElementById('upiUtrInput').focus();
        }

        function closeUpiPaymentModal() {
            document.getElementById('upiPaymentModal').style.display = 'none';
            document.getElementById('upiUtrForm').hidden = true;
            document.getElementById('upiInitialActions').hidden = false;
            document.getElementById('upiUtrForm').reset();
            document.getElementById('upiUtrError').textContent = '';
            pendingUpiPaymentOrderIds = [];
        }

        async function confirmUpiPayment(event) {
            event.preventDefault();
            const form = event.currentTarget;
            const button = form.querySelector('button[type="submit"]');
            button.disabled = true;
            document.getElementById('upiUtrError').textContent = '';
            try {
                const response = await fetch(`${API_BASE_URL}/api/customer/orders/payment`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        Authorization: `Bearer ${currentCustomerAuthToken}`
                    },
                    body: JSON.stringify({
                        orderIds: pendingUpiPaymentOrderIds,
                        utr: document.getElementById('upiUtrInput').value.trim()
                    })
                });
                const result = await readApiResponse(response);
                if (!response.ok) {
                    throw new Error(result.error || 'Could not record the payment confirmation.');
                }
                closeUpiPaymentModal();
                showSuccessToast('Payment UTR submitted.');
                loadCustomerOrders();
                loadAdminData();
            } catch (error) {
                document.getElementById('upiUtrError').textContent =
                    error.message || 'Could not submit the payment UTR.';
            } finally {
                button.disabled = false;
            }
        }

        async function startRazorpayPayment(orderIds, discount = 0) {
            if (!currentCustomerAuthToken) {
                alert('Please log in again before making a payment.');
                return;
            }
            if (!window.Razorpay) {
                await new Promise((resolve, reject) => {
                    const script = document.createElement('script');
                    script.src = 'https://checkout.razorpay.com/v1/checkout.js';
                    script.onload = resolve;
                    script.onerror = () => reject(new Error('Could not load the secure payment window. Check your internet connection.'));
                    document.head.appendChild(script);
                }).catch(error => {
                    alert(error.message);
                });
                if (!window.Razorpay) return;
            }

            let gatewayOrder;
            try {
                const response = await fetch(`${API_BASE_URL}/api/payments/razorpay/create-order`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        Authorization: `Bearer ${currentCustomerAuthToken}`
                    },
                    body: JSON.stringify({ orderIds })
                });
                gatewayOrder = await readApiResponse(response);
                if (!response.ok) throw new Error(gatewayOrder.error || 'Could not start payment.');
            } catch (error) {
                alert(error.message || 'Could not start payment. Your order remains pending; use Pay now to retry.');
                return;
            }

            const checkout = new Razorpay({
                key: gatewayOrder.keyId,
                amount: gatewayOrder.amount,
                currency: gatewayOrder.currency,
                name: 'Mealzy',
                description: 'Food order payment',
                order_id: gatewayOrder.razorpayOrderId,
                config: {
    display: {
        blocks: {
            upi: {
                name: "Pay using UPI",
                instruments: [
                    { method: "upi" }
                ]
            }
        },
        sequence: ["block.upi"],
        preferences: {
            show_default_blocks: true
        }
    }
},
                prefill: {
                    name: gatewayOrder.customerName || '',
                    email: gatewayOrder.customerEmail || ''
                },
                theme: { color: '#171717' },
                handler: async function (response) {
                    try {
                        const verifyResponse = await fetch(`${API_BASE_URL}/api/payments/razorpay/verify`, {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json',
                                Authorization: `Bearer ${currentCustomerAuthToken}`
                            },
                            body: JSON.stringify({
                                razorpay_order_id: response.razorpay_order_id,
                                razorpay_payment_id: response.razorpay_payment_id,
                                razorpay_signature: response.razorpay_signature
                            })
                        });
                        const verification = await readApiResponse(verifyResponse);
                        if (!verifyResponse.ok) {
                            throw new Error(verification.error || 'Payment is not verified yet.');
                        }
                        showOrderSuccessPopup(orderIds, discount);
                        loadCustomerOrders();
                        loadAdminData();
                    } catch (error) {
                        alert((error.message || 'Payment verification is pending.') +
                            ' If money was deducted, do not pay again immediately; refresh My Orders or contact support.');
                        loadCustomerOrders();
                    }
                },
                modal: {
                    ondismiss: function () {
                        loadCustomerOrders();
                    }
                }
            });
            checkout.on('payment.failed', function () {
                alert('Payment failed or was cancelled. Your order remains unpaid; you can retry from My Orders.');
                loadCustomerOrders();
            });
            checkout.open();
        }

        function useCurrentLocation() {
            if (!navigator.geolocation) {
                alert('Location detection is not supported in this browser. Please type your area or city manually.');
                return;
            }

            navigator.geolocation.getCurrentPosition(
                (position) => {
                    const { latitude, longitude } = position.coords;
                    const geoText = `My current location (${latitude.toFixed(5)}, ${longitude.toFixed(5)})`;
                    document.getElementById('deliveryLocation').value = geoText;
                    showSuccessToast('Current location added.');
                },
                () => {
                    alert('Unable to access your current location. Please type the nearest landmark or area instead.');
                },
                { enableHighAccuracy: true, timeout: 15000 }
            );
        }

        function openMapLocationPicker() {
            const address = document.getElementById('deliveryAddress').value.trim();
            const query = address ? `${address} ${document.getElementById('deliveryLocation').value.trim()}`.trim() : 'delivery location';
            const mapsUrl = `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(query)}`;
            window.open(mapsUrl, '_blank', 'noopener,noreferrer');
            alert('Choose your delivery place in Google Maps and paste the selected location text back into the field.');
        }

        async function submitCheckout(event) {
            event.preventDefault();
            const form = event.currentTarget;
            const submitButton = form.querySelector('button[type="submit"]');
            if (submitButton.disabled) return;

            if (!customerCart.length || !currentCustomerEmail) {
                showErrorToast('Your cart is empty.');
                return;
            }

            const address = document.getElementById('deliveryAddress').value.trim();
            const location = document.getElementById('deliveryLocation').value.trim();
            const paymentMethod = document.querySelector('input[name="paymentMode"]:checked')?.value || 'Cash on Delivery';

            if (!address || !location) {
                showErrorToast('Please provide your address and delivery location.');
                return;
            }

            submitButton.disabled = true;
            try {
                const response = await fetch(`${API_BASE_URL}/api/orders`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        items: customerCart.map(item => ({ productId: item.productId, quantity: item.quantity })),
                        couponCode: appliedCoupon?.couponCode || '',
                        customerEmail: currentCustomerEmail,
                        address,
                        location,
                        paymentMethod
                    })
                });
                const result = await readApiResponse(response);
                if (!response.ok) {
                    throw new Error(result.error || 'Could not place order.');
                }

                customerCart = [];
                appliedCoupon = null;
                document.getElementById('cartCouponCode').value = '';
                setCartCouponMessage('');
                renderCustomerCart();
                closeCheckoutModal();
                const orderIds = result.order_ids || [result.order_id];
                if (paymentMethod === 'UPI') {
                    await startRazorpayPayment(orderIds, result.discount);
                } else {
                    showOrderSuccessPopup(orderIds, result.discount);
                }
                await loadCustomerOrders();
                loadProducts().catch(error => {
                    console.error('Order was placed, but the product list could not be refreshed.', error);
                });
            } catch (error) {
                showErrorToast(error.message || 'Could not place order. Please try again.');
            } finally {
                submitButton.disabled = false;
            }
        }

        async function deleteProduct(productId) {
            const confirmed = window.confirm('Delete this product from the marketplace?');
            if (!confirmed) return;

            try {
                const response = await fetch(`${API_BASE_URL}/api/products/${productId}`, {
                    method: 'DELETE'
                });
                const result = await readApiResponse(response);
                if (!response.ok) {
                    throw new Error(result.error || 'Could not delete product.');
                }
                showSuccessToast(result.message || 'Product deleted successfully.');
                await loadAdminData();
                await loadProducts();
            } catch (error) {
                showErrorToast(error.message || 'Could not delete product.');
            }
        }

        async function addProduct(event) {
            event.preventDefault();
            const payload = new FormData();
            payload.append('name', document.getElementById('productName').value);
            payload.append('category', document.getElementById('productCategory').value);
            payload.append('description', document.getElementById('productDescription').value);
            payload.append('price', document.getElementById('productPrice').value);
            payload.append('unit', document.getElementById('productUnit').value);
            payload.append('stock', document.getElementById('productStock').value);
            const image = document.getElementById('productImage').files[0];
            if (image) payload.append('image', image);
            const response = await fetch(`${API_BASE_URL}/api/products`, {
                method: 'POST', body: payload
            });
            const result = await readApiResponse(response);
            if (!response.ok) {
                alert(result.error || 'Could not add product.');
                return;
            }
            event.target.reset();
            showSuccessToast('Product added successfully.');
            loadAdminData();
        }

        async function saveProductChanges(event, productId) {
            event.preventDefault();
            const form = event.currentTarget;
            const submitButton = form.querySelector('button[type="submit"]');
            submitButton.disabled = true;
            try {
                const response = await fetch(`${API_BASE_URL}/api/products/${productId}`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        price: Number(form.elements.price.value),
                        stock: Number(form.elements.stock.value)
                    })
                });
                const result = await readApiResponse(response);
                if (!response.ok) {
                    throw new Error(result.error || 'Could not update product.');
                }
                showSuccessToast(result.message || 'Product updated successfully.');
                await loadAdminData();
                await loadProducts();
            } catch (error) {
                showErrorToast(error.message || 'Could not update product.');
            } finally {
                submitButton.disabled = false;
            }
        }

        const savedCustomerSession = sessionStorage.getItem('customerSession');
        if (savedCustomerSession) {
            try {
                const customerSession = JSON.parse(savedCustomerSession);
                if (customerSession.email && customerSession.token) {
                    currentCustomerEmail = customerSession.email;
                    currentCustomerName = customerSession.name || '';
                    currentCustomerAuthToken = customerSession.token;
                    showMarketplace('customerMarketplace');
                    document.getElementById('customerProfileName').textContent =
                        currentCustomerName || 'Customer';
                    document.getElementById('customerProfileEmail').textContent = currentCustomerEmail;
                    loadProducts();
                    loadCustomerOrders();
                } else {
                    sessionStorage.removeItem('customerSession');
                }
            } catch (error) {
                console.error('Could not restore the customer session.', error);
                sessionStorage.removeItem('customerSession');
            }
        }

        const pendingRegistrationEmail = sessionStorage.getItem('pendingRegistrationEmail');
        if (pendingRegistrationEmail) {
            document.getElementById('registrationEmail').value = pendingRegistrationEmail;
            document.getElementById('verificationEmail').textContent = pendingRegistrationEmail;
            document.getElementById('registrationFormView').style.display = 'none';
            document.getElementById('verificationStep').classList.add('active');
            document.getElementById('registration').classList.add('active');
            document.querySelectorAll('.login-form').forEach(form => form.classList.remove('active'));
            document.querySelectorAll('.tab').forEach(tab => tab.classList.remove('active'));
        }