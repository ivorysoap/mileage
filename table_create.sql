CREATE TABLE `records` (
	`uuid` VARCHAR(50) NOT NULL COLLATE 'utf8mb4_0900_ai_ci',
	`date` DATE NOT NULL,
	`fuelPrice` FLOAT NOT NULL DEFAULT '0' COMMENT '$/L',
	`volumeFilled` FLOAT NOT NULL DEFAULT '0' COMMENT 'L',
	`distanceDriven` FLOAT NOT NULL DEFAULT '0' COMMENT 'km',
	`notes` TEXT NOT NULL COLLATE 'utf8mb4_0900_ai_ci',
	`mileage_l100km` FLOAT NULL,
	`mileage_mpg` FLOAT NULL
)
COLLATE='utf8mb4_0900_ai_ci'
ENGINE=InnoDB
;
