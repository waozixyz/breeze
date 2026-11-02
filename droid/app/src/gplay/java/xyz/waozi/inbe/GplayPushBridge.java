package xyz.waozi.inbe;

final class GplayPushBridge {
    private GplayPushBridge() {}

    static String[] getDistributors(MainActivity activity) {
        return new String[] {"fcm"};
    }

    static String[] getDistributorLabels(MainActivity activity) {
        return new String[] {activity.getString(R.string.push_google_name)};
    }

    static String[] getDistributorIcons(MainActivity activity) {
        return new String[] {""};
    }

}
