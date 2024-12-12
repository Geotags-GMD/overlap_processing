from qgis.utils import iface

def run_main_script():
    import processing
    from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QComboBox, QPushButton, QApplication
    from PyQt5.QtCore import QVariant
    from qgis.core import QgsField, QgsProject, QgsVectorLayer, QgsFeature
    import sys

    # Create a dialog class to select option
    class OptionSelectionDialog(QDialog):
        def __init__(self, parent=None):
            super().__init__(parent)
            self.setWindowTitle('Select Option')
            self.setLayout(QVBoxLayout())

            self.option_combo = QComboBox()
            self.option_combo.addItems(['No Decision', 'With Resolution or Agreement'])
            self.layout().addWidget(QLabel('Select the Case Type:'))
            self.layout().addWidget(self.option_combo)

            self.ok_button = QPushButton('OK')
            self.ok_button.clicked.connect(self.accept)
            self.layout().addWidget(self.ok_button)

        def get_selected_option(self):
            return self.option_combo.currentText()

    # Create and show the dialog
    dialog = OptionSelectionDialog()
    if not dialog.exec_():
        raise Exception("Option selection canceled")

    selected_option = dialog.get_selected_option()

    # Define Option A code block
    def option_a_code():
    # Create a dialog class to select layers
        class LayerSelectionDialog(QDialog):
            def __init__(self, parent=None):
                super().__init__(parent)
                self.setWindowTitle('Select Layers')
                self.setLayout(QVBoxLayout())

                self.ND1_layer = None
                self.ND2_layer = None
                self.ND1_EA_layer = None
                self.ND2_EA_layer = None

                layer_names = [layer.name() for layer in QgsProject.instance().mapLayers().values()]

                # Filter layers for ND1 and ND2 selection (only 14 character names excluding those with "_landmark")
                ea_layer_names = [name for name in layer_names if len(name) == 14 and "_landmark" not in name]

                self.ND1_combo = QComboBox()
                self.ND1_combo.addItems(ea_layer_names)
                self.layout().addWidget(QLabel('Select the layer for the first area with No Decision'))
                self.layout().addWidget(self.ND1_combo)

                self.ND2_combo = QComboBox()
                self.ND2_combo.addItems(ea_layer_names)
                self.layout().addWidget(QLabel('Select the layer for the second area with No Decision'))
                self.layout().addWidget(self.ND2_combo)

                self.ND1_EA_combo = QComboBox()
                self.layout().addWidget(QLabel('Select the ea2024 layer of the first area selected'))
                self.layout().addWidget(self.ND1_EA_combo)

                self.ND2_EA_combo = QComboBox()
                self.layout().addWidget(QLabel('Select the ea2024 layer of the second area selected'))
                self.layout().addWidget(self.ND2_EA_combo)

                self.ok_button = QPushButton('OK')
                self.ok_button.clicked.connect(self.accept)
                self.layout().addWidget(self.ok_button)

                self.ND1_combo.currentIndexChanged.connect(self.update_ND1_EA_combo)
                self.ND2_combo.currentIndexChanged.connect(self.update_ND2_EA_combo)

            def update_ND1_EA_combo(self):
                ND1_EA_name_prefix = f"{self.ND1_combo.currentText()[:5]}_ea2024"
                layer_names = [layer.name() for layer in QgsProject.instance().mapLayers().values()]
                reference_layer_names_ND1 = [name for name in layer_names if name.startswith(ND1_EA_name_prefix)]
                self.ND1_EA_combo.clear()
                self.ND1_EA_combo.addItems(reference_layer_names_ND1)

            def update_ND2_EA_combo(self):
                ND2_EA_name_prefix = f"{self.ND2_combo.currentText()[:5]}_ea2024"
                layer_names = [layer.name() for layer in QgsProject.instance().mapLayers().values()]
                reference_layer_names_ND2 = [name for name in layer_names if name.startswith(ND2_EA_name_prefix)]
                self.ND2_EA_combo.clear()
                self.ND2_EA_combo.addItems(reference_layer_names_ND2)

            def accept(self):
                self.ND1_layer = QgsProject.instance().mapLayersByName(self.ND1_combo.currentText())[0]
                self.ND2_layer = QgsProject.instance().mapLayersByName(self.ND2_combo.currentText())[0]
                self.ND1_EA_layer = QgsProject.instance().mapLayersByName(self.ND1_EA_combo.currentText())[0]
                self.ND2_EA_layer = QgsProject.instance().mapLayersByName(self.ND2_EA_combo.currentText())[0]
                super().accept()

        # Create and show the dialog

        dialog = LayerSelectionDialog()
        if not dialog.exec_():
            raise Exception("Layer selection canceled")

        ND1_layer = dialog.ND1_layer
        ND2_layer = dialog.ND2_layer
        ND1_EA_layer = dialog.ND1_EA_layer
        ND2_EA_layer = dialog.ND2_EA_layer

        # Create a temporary memory layer to store the results with a name based on ND1 layer
        output_layer_name_ND1 = f"{ND1_layer.name()}_ND1"
        output_layer_ND1 = QgsVectorLayer("Point?crs=EPSG:4326", output_layer_name_ND1, "memory")
        output_layer_provider_ND1 = output_layer_ND1.dataProvider()

        # Add the fields from the ND1 layer to the output layer
        output_layer_provider_ND1.addAttributes(ND1_layer.fields())

        # Add the new fields to the output layer
        output_layer_provider_ND1.addAttributes([
            QgsField('TRANS_ID', QVariant.String),
            QgsField('PREV_ID', QVariant.String),
            QgsField('CASE', QVariant.String)
        ])
        output_layer_ND1.updateFields()

        # Fetch the Geocode value from the first row of ND2
        first_geocode_value_ND2 = None
        for feature in ND2_layer.getFeatures():
            first_geocode_value_ND2 = feature['GEOCODE']
            break

        if first_geocode_value_ND2 is None:
            raise Exception("No Geocode value found in ND2 layer")

        # Define a function to add points to the output layer
        def add_points_within_ND2(points_layer, reference_layer, output_layer, case_value):
            for point_feature in points_layer.getFeatures():
                point_geometry = point_feature.geometry()
                is_within_polygon = False
                prev_id_value = point_feature['CBMS_GEOID']
                for reference_feature in reference_layer.getFeatures():
                    reference_geometry = reference_feature.geometry()
                    if reference_geometry.contains(point_geometry) and reference_feature['GEOCODE'] == first_geocode_value_ND2:
                        is_within_polygon = True
                        break

                new_feature = QgsFeature(output_layer.fields())
                new_feature.setGeometry(point_geometry)
                if is_within_polygon:
                    attributes = point_feature.attributes() + [None, prev_id_value, case_value]
                else:
                    attributes = point_feature.attributes() + [None, None, None]
                new_feature.setAttributes(attributes)
                output_layer.dataProvider().addFeature(new_feature)

        # Add points from ND1 layer to the output layer with the appropriate CASE value and ID values
        add_points_within_ND2(ND1_layer, ND2_EA_layer, output_layer_ND1, 'NO_DECISION')

        # Add the output layer to the QGIS project
        QgsProject.instance().addMapLayer(output_layer_ND1)
        print(f"Processing complete. Check the '{output_layer_name_ND1}' layer.")


        # Create a temporary memory layer to store the results with a name based on ND2 layer
        output_layer_name_ND2 = f"{ND2_layer.name()}_ND2"
        output_layer_ND2 = QgsVectorLayer("Point?crs=EPSG:4326", output_layer_name_ND2, "memory")
        output_layer_provider_ND2 = output_layer_ND2.dataProvider()

        # Add the fields from the ND1 layer to the output layer
        output_layer_provider_ND2.addAttributes(ND2_layer.fields())

        # Add the new fields to the output layer
        output_layer_provider_ND2.addAttributes([
            QgsField('TRANS_ID', QVariant.String),
            QgsField('PREV_ID', QVariant.String),
            QgsField('CASE', QVariant.String)
        ])
        output_layer_ND2.updateFields()

        # Fetch the Geocode value from the first row of ND2
        first_geocode_value_ND1 = None
        for feature in ND1_layer.getFeatures():
            first_geocode_value_ND1 = feature['GEOCODE']
            break

        if first_geocode_value_ND1 is None:
            raise Exception("No Geocode value found in ND1 layer")

        # Define a function to add points to the output layer
        def add_points_within_ND1(points_layer, reference_layer, output_layer, case_value):
            for point_feature in points_layer.getFeatures():
                point_geometry = point_feature.geometry()
                is_within_polygon = False
                prev_id_value = point_feature['CBMS_GEOID']
                for reference_feature in reference_layer.getFeatures():
                    reference_geometry = reference_feature.geometry()
                    if reference_geometry.contains(point_geometry) and reference_feature['GEOCODE'] == first_geocode_value_ND1:
                        is_within_polygon = True
                        break

                new_feature = QgsFeature(output_layer.fields())
                new_feature.setGeometry(point_geometry)
                if is_within_polygon:
                    attributes = point_feature.attributes() + [None, prev_id_value, case_value]
                else:
                    attributes = point_feature.attributes() + [None, None, None]
                new_feature.setAttributes(attributes)
                output_layer.dataProvider().addFeature(new_feature)

        # Add points from ND1 layer to the output layer with the appropriate CASE value and ID values
        add_points_within_ND1(ND2_layer, ND1_EA_layer, output_layer_ND2, 'NO_DECISION')

        # Add the output layer to the QGIS project
        QgsProject.instance().addMapLayer(output_layer_ND2)

        print(f"Processing complete. Check the '{output_layer_name_ND2}' layer.")

    # Define Option B code block
    def option_b_code():
        # Create a dialog class to select layers
        class LayerSelectionDialog(QDialog):
            def __init__(self, parent=None):
                super().__init__(parent)
                self.setWindowTitle('Select Layers')
                self.setLayout(QVBoxLayout())

                self.transferEA_layer = None
                self.prevailingEA_layer = None
                self.referenceEA_layer = None

                layer_names = [layer.name() for layer in QgsProject.instance().mapLayers().values()]

                # Filter layers for TransferEA and PrevailingEA selection (only 14 character names)
                ea_layer_names = [name for name in layer_names if len(name) == 14 and "_landmark" not in name]

                self.prevailingEA_combo = QComboBox()
                self.prevailingEA_combo.addItems(ea_layer_names)
                self.layout().addWidget(QLabel('Select the Prevailing EA layer'))
                self.layout().addWidget(self.prevailingEA_combo)

                self.transferEA_combo = QComboBox()
                self.transferEA_combo.addItems(ea_layer_names)
                self.layout().addWidget(QLabel('Select the Transfer EA layer'))
                self.layout().addWidget(self.transferEA_combo)

                self.referenceEA_combo = QComboBox()
                self.layout().addWidget(QLabel('Select the ea2024 layer of the Prevailing EA'))
                self.layout().addWidget(self.referenceEA_combo)

                self.ok_button = QPushButton('OK')
                self.ok_button.clicked.connect(self.accept)
                self.layout().addWidget(self.ok_button)

                self.prevailingEA_combo.currentIndexChanged.connect(self.update_reference_combo)

            def update_reference_combo(self):
                prevailingEA_name_prefix = f"{self.prevailingEA_combo.currentText()[:5]}_ea2024"
                layer_names = [layer.name() for layer in QgsProject.instance().mapLayers().values()]
                reference_layer_names = [name for name in layer_names if name.startswith(prevailingEA_name_prefix)]
                self.referenceEA_combo.clear()
                self.referenceEA_combo.addItems(reference_layer_names)

            def accept(self):
                self.transferEA_layer = QgsProject.instance().mapLayersByName(self.transferEA_combo.currentText())[0]
                self.prevailingEA_layer = QgsProject.instance().mapLayersByName(self.prevailingEA_combo.currentText())[0]
                self.referenceEA_layer = QgsProject.instance().mapLayersByName(self.referenceEA_combo.currentText())[0]
                super().accept()

        # Create and show the dialog
        dialog = LayerSelectionDialog()
        if not dialog.exec_():
            raise Exception("Layer selection canceled")

        transferEA_layer = dialog.transferEA_layer
        prevailingEA_layer = dialog.prevailingEA_layer
        referenceEA_layer = dialog.referenceEA_layer

        # Fetch the Geocode value from the first row of PrevailingEA
        first_geocode_value = None
        for feature in prevailingEA_layer.getFeatures():
            first_geocode_value = feature['GEOCODE']
            break

        if first_geocode_value is None:
            raise Exception("No Geocode value found in Prevailing EA layer")

        # Create a temporary memory layer to store the results with a name based on TransferEA layer
        output_layer_name = f"{prevailingEA_layer.name()}_RA"
        output_layer = QgsVectorLayer("Point?crs=EPSG:4326", output_layer_name, "memory")
        output_layer_provider = output_layer.dataProvider()

        # Add the fields from the TransferEA layer to the output layer
        output_layer_provider.addAttributes(transferEA_layer.fields())
        # Add the new fields to the output layer
        output_layer_provider.addAttributes([
            QgsField('TRANS_ID', QVariant.String),
            QgsField('PREV_ID', QVariant.String),
            QgsField('CASE', QVariant.String)
        ])
        output_layer.updateFields()

        # Define a function to add points to the output layer
        def add_points_within_reference(points_layer, reference_layer, output_layer, case_value, prev_id_value=None, trans_id_value=None):
            for point_feature in points_layer.getFeatures():
                point_geometry = point_feature.geometry()
                for reference_feature in reference_layer.getFeatures():
                    reference_geometry = reference_feature.geometry()
                    if reference_geometry.contains(point_geometry) and reference_feature['GEOCODE'] == prev_id_value:
                        new_feature = QgsFeature(output_layer.fields())
                        new_feature.setGeometry(point_geometry)
                        trans_id = point_feature['CBMS_GEOID'] if trans_id_value else None
                        attributes = point_feature.attributes() + [trans_id, prev_id_value, case_value]
                        new_feature.setAttributes(attributes)
                        output_layer.dataProvider().addFeature(new_feature)

        # Fetch the TRANS_ID value from the TransferEA layer
        for feature in transferEA_layer.getFeatures():
            transfer_EA_transID = feature['CBMS_GEOID']
            break

        # Add points from TransferEA and PrevailingEA layers to the output layer with the appropriate CASE value and ID values
        add_points_within_reference(transferEA_layer, referenceEA_layer, output_layer, 'WITH_RESOLUTION_AGREEMENT', first_geocode_value, transfer_EA_transID)
        add_points_within_reference(prevailingEA_layer, referenceEA_layer, output_layer, None, first_geocode_value)

        # Add the output layer to the QGIS project
        QgsProject.instance().addMapLayer(output_layer)

        print(f"Processing complete. Check the '{output_layer_name}' layer.")
    if selected_option == 'No Decision':
        option_a_code()
    elif selected_option == 'With Resolution or Agreement':
        option_b_code()