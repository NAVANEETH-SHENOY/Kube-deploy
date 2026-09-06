document.addEventListener('DOMContentLoaded', () => {

    // ── Sidebar Toggle (Mobile) ───────────────────────────────────────────────
    const sidebar       = document.getElementById('app-sidebar');
    const sidebarToggle = document.getElementById('sidebar-toggle');
    const sidebarClose  = document.getElementById('sidebar-close');
    const overlay       = document.getElementById('sidebar-overlay');

    function openSidebar() {
        sidebar.classList.add('active');
        overlay.classList.add('active');
        document.body.style.overflow = 'hidden';
    }

    function closeSidebar() {
        sidebar.classList.remove('active');
        overlay.classList.remove('active');
        document.body.style.overflow = '';
    }

    if (sidebarToggle) sidebarToggle.addEventListener('click', openSidebar);
    if (sidebarClose)  sidebarClose.addEventListener('click', closeSidebar);
    if (overlay)       overlay.addEventListener('click', closeSidebar);

    window.addEventListener('resize', () => {
        if (window.innerWidth > 768) closeSidebar();
    });


    // ── Shared helpers ────────────────────────────────────────────────────────
    const MONTH_NAMES = ["JAN","FEB","MAR","APR","MAY","JUN","JUL","AUG","SEP","OCT","NOV","DEC"];

    function isUpcoming(dateStr) {
        const today = new Date();
        today.setHours(0, 0, 0, 0);
        return new Date(dateStr + 'T00:00:00') >= today;
    }


    // ── Overview / Dashboard page ─────────────────────────────────────────────
    const recentEventsList = document.getElementById('recent-events-list');
    const statTotal        = document.getElementById('stat-total');

    if (recentEventsList) {

        // Show a simple spinner inside the card body while loading
        recentEventsList.innerHTML =
            '<div class="list-loader"><span class="spinner"></span> Loading events…</div>';

        fetch('/api/events')
            .then(res => {
                if (!res.ok) throw new Error('API error');
                return res.json();
            })
            .then(events => {

                // ── Populate stats ──────────────────────────────────────────
                if (statTotal) {
                    const today = new Date();
                    today.setHours(0, 0, 0, 0);

                    const upcomingCount  = events.filter(e => isUpcoming(e.date)).length;
                    const categories     = new Set(events.map(e => e.category)).size;
                    const venues         = new Set(events.map(e => e.venue)).size;

                    document.getElementById('stat-total').textContent      = events.length;
                    document.getElementById('stat-upcoming').textContent   = upcomingCount;
                    document.getElementById('stat-categories').textContent = categories;
                    document.getElementById('stat-venues').textContent     = venues;
                }

                // ── Populate recent events list ─────────────────────────────
                if (events.length === 0) {
                    recentEventsList.innerHTML =
                        '<div class="empty-list">No events yet. Create your first event!</div>';
                    return;
                }

                recentEventsList.innerHTML = '';

                // Show 4 nearest upcoming; fall back to 4 latest if none upcoming
                const upcoming = events.filter(e => isUpcoming(e.date));
                const toShow   = (upcoming.length > 0 ? upcoming : events).slice(0, 4);

                toShow.forEach(evt => {
                    const dateParts = evt.date.split('-');
                    let monthStr = 'UNK', dayStr = '00';
                    if (dateParts.length === 3) {
                        monthStr = MONTH_NAMES[parseInt(dateParts[1], 10) - 1] || monthStr;
                        dayStr   = parseInt(dateParts[2], 10);
                    }
                    const upcomingEvt = isUpcoming(evt.date);

                    recentEventsList.insertAdjacentHTML('beforeend', `
                        <a href="/event/${evt.id}" class="event-list-item">
                            <div class="event-date-box">
                                <span class="month">${monthStr}</span>
                                <span class="day">${dayStr}</span>
                            </div>
                            <div class="event-info">
                                <h4>${evt.title}</h4>
                                <p>
                                    <i data-lucide="map-pin"></i> ${evt.venue}
                                    &middot;
                                    <i data-lucide="clock"></i> ${evt.time}
                                </p>
                            </div>
                            <div class="event-status ${upcomingEvt ? 'status-upcoming' : 'status-past'}">
                                ${upcomingEvt ? 'Upcoming' : 'Past'}
                            </div>
                        </a>
                    `);
                });

                if (typeof lucide !== 'undefined') lucide.createIcons();
            })
            .catch(err => {
                console.error('Dashboard fetch error:', err);
                recentEventsList.innerHTML =
                    '<div class="empty-list error-text">Could not load events. Check your connection.</div>';

                // Zero out stats on error
                ['stat-total','stat-upcoming','stat-categories','stat-venues'].forEach(id => {
                    const el = document.getElementById(id);
                    if (el) el.textContent = '--';
                });
            });
    }

});
