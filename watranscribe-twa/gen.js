const { TwaManifest, TwaGenerator, BufferedLog, ConsoleLog } = require('@bubblewrap/core');

async function main() {
  const manifest = await TwaManifest.fromWebManifest(
    'https://transcribe.flyboybyte.com/static/manifest.json'
  );

  manifest.packageId = 'com.flyboybyte.watranscribe';
  manifest.name = 'WAtranscribe';
  manifest.launcherName = 'WAtranscribe';
  manifest.signingKey = {
    path: '/home/logan/@flyboybyte__drag-tree.jks',
    alias: 'e2f4affc23a7141f202d26f6d9f2d4d0',
  };

  const err = manifest.validate();
  if (err) {
    console.error('Validation error:', err);
    process.exit(1);
  }

  await manifest.saveToFile('./twa-manifest.json');
  console.log('Wrote twa-manifest.json');
  console.log('shareTarget:', JSON.stringify(manifest.shareTarget, null, 2));

  const generator = new TwaGenerator();
  const log = new BufferedLog(new ConsoleLog('Generating TWA'));
  await generator.createTwaProject('.', manifest, log, () => {});
  log.flush();
  console.log('Project generated.');
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
