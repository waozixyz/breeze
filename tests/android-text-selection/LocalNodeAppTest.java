import static org.junit.Assert.*;

import android.content.Intent;
import java.io.File;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import org.junit.Rule;
import org.junit.Test;
import org.junit.rules.TemporaryFolder;
import org.junit.runner.RunWith;
import org.robolectric.RobolectricTestRunner;
import org.robolectric.annotation.Config;
import xyz.waozi.inbe.LocalNodeApp;

@RunWith(RobolectricTestRunner.class)
@Config(sdk = {28, 36}, manifest = Config.NONE)
public class LocalNodeAppTest {
    @Rule public TemporaryFolder external = new TemporaryFolder();

    private Intent requested() {
        return new Intent(Intent.ACTION_MAIN).putExtra(LocalNodeApp.EXTRA_LOCAL_NODE_APP, true);
    }

    @Test public void ordinaryLaunchIgnoresOldArcadeAndPreservesItsFile() throws Exception {
        File oldArcade = external.newFile("arcade.zx");
        byte[] contents = "old developer campaign".getBytes(StandardCharsets.UTF_8);
        Files.write(oldArcade.toPath(), contents);

        Intent launcher = new Intent(Intent.ACTION_MAIN).addCategory(Intent.CATEGORY_LAUNCHER);
        assertNull(LocalNodeApp.offered(true, launcher, external.getRoot()));
        Intent shortcut = new Intent("xyz.waozi.inbe.action.OPEN_APP").putExtra("app_name", "arcade");
        assertNull(LocalNodeApp.offered(true, shortcut, external.getRoot()));
        assertArrayEquals(contents, Files.readAllBytes(oldArcade.toPath()));
    }

    @Test public void explicitDebugLaunchCanStillUseOneBundle() throws Exception {
        File bundle = external.newFile("arcade.zx");
        external.newFile("notes.txt");
        external.newFolder("directory.zx");
        assertEquals(bundle, LocalNodeApp.offered(true, requested(), external.getRoot()));
    }

    @Test public void localRequestDoesNotPersistAcrossNormalLaunches() throws Exception {
        File bundle = external.newFile("arcade.zx");
        assertEquals(bundle, LocalNodeApp.offered(true, requested(), external.getRoot()));
        assertNull(LocalNodeApp.offered(true, new Intent(Intent.ACTION_MAIN), external.getRoot()));
        assertNull(LocalNodeApp.offered(true, null, external.getRoot()));
    }

    @Test public void releaseBuildNeverOffersLocalBundles() throws Exception {
        external.newFile("arcade.zx");
        assertNull(LocalNodeApp.offered(false, requested(), external.getRoot()));
    }

    @Test public void missingAndAmbiguousBundlesUseNormalPackages() throws Exception {
        assertNull(LocalNodeApp.offered(true, requested(), null));
        assertNull(LocalNodeApp.offered(true, requested(), external.getRoot()));
        external.newFile("arcade.zx");
        external.newFile("chess.zx");
        assertNull(LocalNodeApp.offered(true, requested(), external.getRoot()));
        assertNull(LocalNodeApp.offered(true, requested(), new File(external.getRoot(), "missing")));
    }
}
