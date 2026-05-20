/**
 * Browser Notification Service for ATS Platform
 * Handles permissions and triggering desktop alerts.
 */

export const requestNotificationPermission = async () => {
    if (!("Notification" in window)) {
        console.warn("This browser does not support desktop notifications.");
        return false;
    }

    if (Notification.permission === "granted") {
        return true;
    }

    if (Notification.permission !== "denied") {
        const permission = await Notification.requestPermission();
        return permission === "granted";
    }

    return false;
};

export const showNotification = (title, options = {}) => {
    if (Notification.permission === "granted") {
        const defaultOptions = {
            icon: '/favicon.ico', // Update path if needed
            badge: '/favicon.ico',
            silent: false,
            ...options
        };
        
        const n = new Notification(title, defaultOptions);
        
        n.onclick = () => {
            window.focus();
            if (options.url) window.location.href = options.url;
            n.close();
        };

        // Auto close after 10 seconds
        setTimeout(() => n.close(), 10000);
        return n;
    }
    return null;
};

export const checkAndNotifyInterviews = (upcomingInterviews) => {
    if (!upcomingInterviews || upcomingInterviews.length === 0) return;

    const now = new Date();
    
    upcomingInterviews.forEach(interview => {
        const interviewTime = new Date(`${interview.date}T${interview.time}`);
        const diffMs = interviewTime - now;
        const diffMins = Math.floor(diffMs / 60000);

        // Notify at exactly 30 mins, 15 mins, and 5 mins
        if (diffMins === 30 || diffMins === 15 || diffMins === 5) {
            const storageKey = `notified_${interview.id}_${diffMins}m`;
            if (!localStorage.getItem(storageKey)) {
                showNotification(`Upcoming Interview: ${interview.candidate_name}`, {
                    body: `Your interview for ${interview.job_title} is starting in ${diffMins} minutes.`,
                    tag: interview.id,
                    data: { interviewId: interview.id }
                });
                localStorage.setItem(storageKey, 'true');
            }
        }
    });
};
