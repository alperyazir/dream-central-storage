import StandaloneAppsManager from 'components/StandaloneAppsManager';

const AppsPage = () => {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Standalone App Templates</h1>
        <p className="text-muted-foreground">
          Upload pre-signed app templates for each platform. These will be
          bundled with book content.
        </p>
      </div>
      <StandaloneAppsManager />
    </div>
  );
};

export default AppsPage;
