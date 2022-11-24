using COSXML;
using COSXML.Auth;
using COSXML.Transfer;

// Check I'm root
if (Environment.UserName != "root")
{
    Console.WriteLine("You must run this program as root");
    Environment.Exit(1);
}

// Read args to determine what file to upload

const string DefaultUploadFilePath = "/tmp/data.tar.xz";
string uploadFilePath = DefaultUploadFilePath;
string? uploadDestinationPath = null;
if (args.Length == 0)
{
    Console.WriteLine("You don't specify the file to upload, will upload /tmp/data.tar.xz by default.");
    Console.WriteLine("You don't specify the destination to upload, will use timestamp with proper file extension.");
}
else if (args.Length == 1)
{
    if (args[0].Length == 0)
    {
        Console.Error.WriteLine("File to upload can't be empty string.");
        Environment.Exit(2);
    }
    uploadFilePath = args[0];
    Console.WriteLine("You don't specify the destination to upload, will use timestamp with proper file extension.");
}
else if (args.Length == 2)
{
    if (args[0].Length == 0)
    {
        Console.Error.WriteLine("File to upload can't be empty string.");
        Environment.Exit(2);
    }

    if (args[1].Length == 0)
    {
        Console.Error.WriteLine("Destination to upload can't be empty string.");
        Environment.Exit(2);
    }

    uploadFilePath = args[0];
    uploadDestinationPath = args[1];
}
else
{
    // Write to stderr
    Console.Error.WriteLine("You can only specify one optional file and one optional destination to upload.");
    Environment.Exit(2);
}

// Check the upload exists
if (!File.Exists(uploadFilePath))
{
    Console.Error.WriteLine($"The file {uploadFilePath} doesn't exist.");
    Environment.Exit(3);
}

// Check the upload file is not a directory
if (File.GetAttributes(uploadFilePath).HasFlag(FileAttributes.Directory))
{
    Console.Error.WriteLine($"The file {uploadFilePath} is a directory.");
    Environment.Exit(4);
}

// Get config from environment variables
var configNameList = new List<string>{
    "CRUPEST_AUTO_BACKUP_COS_SECRET_ID",
    "CRUPEST_AUTO_BACKUP_COS_SECRET_KEY",
    "CRUPEST_AUTO_BACKUP_COS_REGION",
    "CRUPEST_AUTO_BACKUP_BUCKET_NAME"
};

var config = new Dictionary<string, string>();
foreach (var configName in configNameList)
{
    var configValue = Environment.GetEnvironmentVariable(configName);
    if (configValue is null)
    {
        Console.Error.WriteLine($"Environment variable {configName} is required.");
        Environment.Exit(5);
    }
    config.Add(configName, configValue);
}

var cosConfig = new CosXmlConfig.Builder()
    .IsHttps(true)
    .SetRegion(config["CRUPEST_AUTO_BACKUP_COS_REGION"])
    .Build();

QCloudCredentialProvider cosCredentialProvider =
    new DefaultQCloudCredentialProvider(
        config["CRUPEST_AUTO_BACKUP_COS_SECRET_ID"],
        config["CRUPEST_AUTO_BACKUP_COS_SECRET_KEY"],
        60
    );

CosXml cosXml = new CosXmlServer(cosConfig, cosCredentialProvider);

TransferConfig transferConfig = new TransferConfig();

TransferManager transferManager = new TransferManager(cosXml, transferConfig);

if (uploadDestinationPath is null)
{
    var uploadFileName = Path.GetFileName(uploadFilePath);
    var firstDotPosition = uploadFileName.IndexOf('.');
    uploadDestinationPath = DateTime.Now.ToString("s");
    if (firstDotPosition != -1)
    {
        uploadDestinationPath += uploadFileName.Substring(firstDotPosition + 1);
    }
}

Console.WriteLine($"Upload file source: {uploadFilePath}");
Console.WriteLine($"Upload COS region: {config["CRUPEST_AUTO_BACKUP_COS_REGION"]}");
Console.WriteLine($"Upload bucket name: {config["CRUPEST_AUTO_BACKUP_BUCKET_NAME"]}");
Console.WriteLine($"Upload file destination: {uploadDestinationPath}");

// 上传对象
COSXMLUploadTask uploadTask = new COSXMLUploadTask(config["CRUPEST_AUTO_BACKUP_BUCKET_NAME"], uploadDestinationPath);
uploadTask.SetSrcPath(uploadFilePath);

uploadTask.progressCallback = delegate (long completed, long total)
{
    Console.WriteLine(String.Format("progress = {0:##.##}%", completed * 100.0 / total));
};

try
{
    COSXMLUploadTask.UploadTaskResult result = await transferManager.UploadAsync(uploadTask);
    Console.WriteLine(result.GetResultInfo());
    Console.WriteLine("Upload completed!");
}
catch (Exception e)
{
    Console.Error.WriteLine("CosException: " + e);
    Environment.Exit(6);
}
