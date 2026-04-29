import React from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";

type ModuleCardProps = {
  title: string;
  subtitle: string;
  onPress: () => void;
};

export function ModuleCard({ title, subtitle, onPress }: ModuleCardProps): JSX.Element {
  return (
    <Pressable style={styles.card} onPress={onPress}>
      <View>
        <Text style={styles.title}>{title}</Text>
        <Text style={styles.subtitle}>{subtitle}</Text>
      </View>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  card: {
    padding: 16,
    borderRadius: 10,
    borderWidth: 1,
    borderColor: "#d0d7de",
    marginBottom: 12,
    backgroundColor: "#ffffff",
  },
  title: {
    fontSize: 16,
    fontWeight: "700",
    color: "#1f2937",
  },
  subtitle: {
    marginTop: 4,
    fontSize: 13,
    color: "#4b5563",
  },
});
