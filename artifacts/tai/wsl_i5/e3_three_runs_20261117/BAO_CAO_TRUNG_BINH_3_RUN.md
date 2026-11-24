# E3 — trung bình cộng của3run độc lập

Mỗi run gồm3batch×3lượt; tổng27case30M,29.970request. Mọi run dùng cùng commit, protocol và manifest hash.
Mỗi giá trị trung bình cuối là mean(mean3lượt_run1, mean3lượt_run2, mean3lượt_run3). Vì các run có cùng sốlượt, giá trị này cũng bằng mean9sốđo của mỗi batch.
Throughput được lấy trung bình riêng từ throughput từnglượt; không tính N chia trung bình thời gian.
SD giữa run được tính trên3run-means, không phải khoảng tin cậy. Sốmedian trước đây được giữ trong hồ sơ từngrun, không đổi nhãn thành mean.

|Batch|Run1 mean ACK(s)|Run2 mean ACK(s)|Run3 mean ACK(s)|Mean3run ACK(s)|Mean throughput(rows/s)|Mean active storage(MiB)|
|---:|---:|---:|---:|---:|---:|---:|
|10,000|286.442|332.889|409.884|343.072|92,529|499.064|
|100,000|90.853|173.287|160.482|141.541|250,358|499.763|
|1,000,000|50.501|111.678|133.341|98.506|410,617|499.949|

## Minh chứng từng run

1. e3main_v2_20261117: config, input_manifest, environment, 9caseCSV, verification, hình và ZIP raw logs riêng.
2. e3repeat2_v2_20261117: config, input_manifest, environment, 9caseCSV, verification, hình và ZIP raw logs riêng.
3. e3repeat3_v2_20261117: config, input_manifest, environment, 9caseCSV, verification, hình và ZIP raw logs riêng.

Đã kiểm tra 29,970query_id và27table UUID không trùng giữa cácrun.
Khác biệt mẫu pilot/curator lock và các giới hạn đã công bố của run đầu vẫn áp dụng. Giữ nguyên fsync1, background merges tự nhiên, không xóa cache OS. Các bảng từ run trước được giữ; ổn định quan sát không bảo đảm không có merge tương lai. Chỉ kết luận trong môi trường/workload đã đo.
