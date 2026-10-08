% 最短路径问题 - 极简动态规划解法
clear; clc;

%% 第一步：定义问题和地图
% 城市编号：1-S, 2-A1, 3-A2, 4-A3, 5-B1, 6-B2, 7-B3, 8-C1, 9-C2, 10-T

% 道路距离表（邻接矩阵）
D = [0, 2, 5, 1, Inf, Inf, Inf, Inf, Inf, Inf;
    Inf, 0, Inf, Inf, 12, 14, Inf, Inf, Inf, Inf;
    Inf, Inf, 0, Inf, 6, 10, 4, Inf, Inf, Inf;
    Inf, Inf, Inf, 0, 13, 12, 11, Inf, Inf, Inf;
    Inf, Inf, Inf, Inf, 0, Inf, Inf, 3, 9, Inf;
    Inf, Inf, Inf, Inf, Inf, 0, Inf, 6, 5, Inf;
    Inf, Inf, Inf, Inf, Inf, Inf, 0, 8, 10, Inf;
    Inf, Inf, Inf, Inf, Inf, Inf, Inf, 0, Inf, 5;
    Inf, Inf, Inf, Inf, Inf, Inf, Inf, Inf, 0, 2;
    Inf, Inf, Inf, Inf, Inf, Inf, Inf, Inf, Inf, 0];

% 城市名称（方便显示）
city = {'S', 'A1', 'A2', 'A3', 'B1', 'B2', 'B3', 'C1', 'C2', 'T'};

n = 10;  % 城市总数
start = 1;  % 起点S
target = 10; % 终点T

%% 第二步：初始化动态规划表
dist = inf(1, n);  % 从每个城市到T的最短距离
next = zeros(1, n); % 从每个城市出发的下一站

% 边界条件：从终点T到自己的距离是0
dist(target) = 0;
next(target) = target;

fprintf('=== 开始动态规划计算 ===\n');

%% 第三步：从后往前计算（核心思想！）
% 阶段4：C1, C2 到 T
fprintf('\n--- 阶段4：计算C1,C2到T ---\n');
for i = 8:9  % C1和C2
    dist(i) = D(i, target);
    next(i) = target;
    fprintf('从 %s 到 T: 距离 = %d\n', city{i}, dist(i));
end

% 阶段3：B1, B2, B3 到 T
fprintf('\n--- 阶段3：计算B1,B2,B3到T ---\n');
for i = 5:7  % B1, B2, B3
    min_val = inf;
    best_j = 0;
    
    for j = 8:9  % 只能去C1或C2
        if D(i, j) ~= Inf
            total = D(i, j) + dist(j);
            fprintf('  %s → %s → T: %d + %d = %d\n', ...
                   city{i}, city{j}, D(i, j), dist(j), total);
            
            if total < min_val
                min_val = total;
                best_j = j;
            end
        end
    end
    
    dist(i) = min_val;
    next(i) = best_j;
    fprintf('  %s 的最优选择: → %s, 总距离 = %d\n', ...
           city{i}, city{best_j}, min_val);
end

% 阶段2：A1, A2, A3 到 T
fprintf('\n--- 阶段2：计算A1,A2,A3到T ---\n');
for i = 2:4  % A1, A2, A3
    min_val = inf;
    best_j = 0;
    
    for j = 5:7  % 只能去B1,B2,B3
        if D(i, j) ~= Inf
            total = D(i, j) + dist(j);
            fprintf('  %s → %s → T: %d + %d = %d\n', ...
                   city{i}, city{j}, D(i, j), dist(j), total);
            
            if total < min_val
                min_val = total;
                best_j = j;
            end
        end
    end
    
    dist(i) = min_val;
    next(i) = best_j;
    fprintf('  %s 的最优选择: → %s, 总距离 = %d\n', ...
           city{i}, city{best_j}, min_val);
end

% 阶段1：S 到 T
fprintf('\n--- 阶段1：计算S到T ---\n');
i = 1;  % 起点S
min_val = inf;
best_j = 0;

for j = 2:4  % 只能去A1,A2,A3
    if D(i, j) ~= Inf
        total = D(i, j) + dist(j);
        fprintf('  S → %s → T: %d + %d = %d\n', ...
               city{j}, D(i, j), dist(j), total);
        
        if total < min_val
            min_val = total;
            best_j = j;
        end
    end
end

dist(i) = min_val;
next(i) = best_j;
fprintf('  S 的最优选择: → %s, 总距离 = %d\n', city{best_j}, min_val);

%% 第四步：输出最终结果
fprintf('\n=== 最终结果 ===\n');
fprintf('最短路径长度: %d\n', dist(start));

% 找出完整路径
fprintf('最短路径: ');
current = start;
while current ~= target
    fprintf('%s → ', city{current});
    current = next(current);
end
fprintf('%s\n', city{target});