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

// Check the upload file is not bigger than 5G
if (new FileInfo(uploadFilePath).Length > 5L * 1024L * 1024L * 1024L)
{
    Console.Error.WriteLine($"The file {uploadFilePath} is bigger than 5G, which is not support now.");
    Environment.Exit(5);
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

var region = config["CRUPEST_AUTO_BACKUP_COS_REGION"];
var secretId = config["CRUPEST_AUTO_BACKUP_COS_SECRET_ID"];
var secretKey = config["CRUPEST_AUTO_BACKUP_COS_SECRET_KEY"];
var bucketName = config["CRUPEST_AUTO_BACKUP_BUCKET_NAME"];

var credentials = new TencentCloudCOSHelper.Credentials(secretId, secretKey);

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

await using var fileStream = new FileStream(uploadFilePath, FileMode.Open, FileAccess.Read);

// 上传对象
try
{
    await TencentCloudCOSHelper.PutObject(credentials, region, bucketName, uploadDestinationPath, fileStream);
    Console.WriteLine("Upload completed!");
}
catch (Exception e)
{
    Console.Error.WriteLine("Exception: " + e);
    Environment.Exit(6);
}
